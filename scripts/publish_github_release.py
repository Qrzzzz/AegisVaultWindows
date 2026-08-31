"""Publish a verified draft Release without ever overwriting public assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from release_metadata import load_release_metadata


class PublishError(RuntimeError):
    """Raised when remote Release state is unsafe to mutate."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["gh", *arguments],
        check=False,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"gh {' '.join(arguments)} failed: {detail}")
    return result


def _api_json(endpoint: str, *arguments: str, missing_ok: bool = False) -> dict[str, Any] | None:
    result = _run("api", endpoint, *arguments, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        if missing_ok and ("HTTP 404" in detail or "Not Found" in detail):
            return None
        raise PublishError(f"GitHub API request failed for {endpoint}: {detail}")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise PublishError(f"GitHub API returned a non-object for {endpoint}")
    return value


def _normalized_markdown(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip()


def _verify_remote_tag(repo: str, tag: str, commit: str) -> None:
    ref = _api_json(f"repos/{repo}/git/ref/tags/{tag}")
    assert ref is not None
    target = ref.get("object", {})
    if target.get("type") != "tag":
        raise PublishError(f"Remote release tag must be annotated; GitHub reports {target.get('type')!r}")
    tag_object = _api_json(f"repos/{repo}/git/tags/{target.get('sha')}")
    assert tag_object is not None
    peeled = tag_object.get("object", {})
    if peeled.get("type") != "commit" or str(peeled.get("sha", "")).lower() != commit.lower():
        raise PublishError(f"Remote tag/commit mismatch: {tag} does not resolve to {commit}")


def _release(repo: str, tag: str) -> dict[str, Any] | None:
    return _api_json(f"repos/{repo}/releases/tags/{tag}", missing_ok=True)


def _verify_release_metadata(release: dict[str, Any], metadata: dict[str, Any], notes: str) -> None:
    if release.get("tag_name") != metadata["tag"]:
        raise PublishError("Release tag_name does not match validated source metadata")
    if release.get("name") != metadata["release_title"]:
        raise PublishError(f"Release title mismatch: {release.get('name')!r}")
    if bool(release.get("prerelease")):
        raise PublishError("Stable AegisVault releases must not be marked prerelease")
    if _normalized_markdown(str(release.get("body", ""))) != _normalized_markdown(notes):
        raise PublishError("Release body differs from the committed release notes")


def _asset_map(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for asset in release.get("assets", []):
        name = str(asset.get("name", ""))
        if not name or name in assets:
            raise PublishError(f"Release contains an empty or duplicate asset name: {name!r}")
        assets[name] = asset
    return assets


def _verify_asset_metadata(asset: dict[str, Any], local_path: Path) -> None:
    if asset.get("state") != "uploaded":
        raise PublishError(f"Remote asset is not fully uploaded: {local_path.name}")
    if int(asset.get("size", -1)) != local_path.stat().st_size:
        raise PublishError(f"Remote asset size mismatch: {local_path.name}")
    remote_digest = asset.get("digest")
    if remote_digest and remote_digest != f"sha256:{_sha256(local_path)}":
        raise PublishError(f"Remote asset digest mismatch: {local_path.name}")


def _download_and_verify(repo: str, tag: str, local_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="aegisvault-release-download-") as temporary_dir:
        _run(
            "release",
            "download",
            tag,
            "--repo",
            repo,
            "--pattern",
            local_path.name,
            "--dir",
            temporary_dir,
        )
        downloaded = Path(temporary_dir) / local_path.name
        if not downloaded.is_file() or _sha256(downloaded) != _sha256(local_path):
            raise PublishError(f"Downloaded Release asset differs from local candidate: {local_path.name}")


def _verify_attestation(repo: str, tag: str, commit: str, signer_workflow: str, asset: Path) -> None:
    arguments = (
        "attestation",
        "verify",
        str(asset),
        "--repo",
        repo,
        "--signer-workflow",
        signer_workflow,
        "--signer-digest",
        commit,
        "--source-ref",
        f"refs/tags/{tag}",
        "--source-digest",
        commit,
        "--deny-self-hosted-runners",
        "--format",
        "json",
    )
    last_detail = ""
    for delay in (0, 2, 4, 8, 16):
        if delay:
            time.sleep(delay)
        result = _run(*arguments, check=False)
        if result.returncode == 0:
            return
        last_detail = result.stderr.strip() or result.stdout.strip()
    raise PublishError(f"Attestation verification failed for {asset.name}: {last_detail}")


def _verify_exact_assets(
    *,
    repo: str,
    release: dict[str, Any],
    local_assets: dict[str, Path],
    tag: str,
    commit: str,
    signer_workflow: str,
) -> None:
    remote_assets = _asset_map(release)
    if set(remote_assets) != set(local_assets):
        raise PublishError(
            f"Release asset set mismatch: remote={sorted(remote_assets)}, expected={sorted(local_assets)}"
        )
    for name, local_path in sorted(local_assets.items()):
        _verify_asset_metadata(remote_assets[name], local_path)
        _download_and_verify(repo, tag, local_path)
        _verify_attestation(repo, tag, commit, signer_workflow, local_path)


def publish(
    *,
    repo: str,
    tag: str,
    commit: str,
    notes_path: Path,
    assets: list[Path],
    signer_workflow: str,
) -> str:
    metadata = load_release_metadata(expected_tag=tag)
    notes_path = notes_path.resolve(strict=True)
    notes = notes_path.read_text(encoding="utf-8")
    resolved_assets = [asset.resolve(strict=True) for asset in assets]
    local_assets = {asset.name: asset for asset in resolved_assets}
    if len(local_assets) != len(resolved_assets):
        raise PublishError("Local public asset names must be unique")
    if set(local_assets) != set(metadata["public_assets"]):
        raise PublishError(
            f"Local public asset set mismatch: {sorted(local_assets)} != {sorted(metadata['public_assets'])}"
        )
    _verify_remote_tag(repo, tag, commit)

    release = _release(repo, tag)
    created = False
    if release is None:
        _run(
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--verify-tag",
            "--draft",
            "--title",
            metadata["release_title"],
            "--notes-file",
            str(notes_path),
            "--target",
            commit,
        )
        created = True
        release = _release(repo, tag)
        if release is None:
            raise PublishError("GitHub did not return the newly created draft Release")

    _verify_release_metadata(release, metadata, notes)
    if not bool(release.get("draft")):
        _verify_exact_assets(
            repo=repo,
            release=release,
            local_assets=local_assets,
            tag=tag,
            commit=commit,
            signer_workflow=signer_workflow,
        )
        _verify_remote_tag(repo, tag, commit)
        return "published-idempotent"

    existing_assets = _asset_map(release)
    unexpected = set(existing_assets).difference(local_assets)
    if unexpected:
        raise PublishError(f"Draft Release contains unexpected assets: {sorted(unexpected)}")
    for name, remote_asset in existing_assets.items():
        _verify_asset_metadata(remote_asset, local_assets[name])
        _download_and_verify(repo, tag, local_assets[name])
    for name, local_path in sorted(local_assets.items()):
        if name not in existing_assets:
            _run("release", "upload", tag, str(local_path), "--repo", repo)

    release = _release(repo, tag)
    assert release is not None
    _verify_release_metadata(release, metadata, notes)
    _verify_exact_assets(
        repo=repo,
        release=release,
        local_assets=local_assets,
        tag=tag,
        commit=commit,
        signer_workflow=signer_workflow,
    )
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise PublishError("Draft Release has no numeric API id")
    _verify_remote_tag(repo, tag, commit)
    _api_json(f"repos/{repo}/releases/{release_id}", "--method", "PATCH", "-F", "draft=false")
    published = _release(repo, tag)
    if published is None or bool(published.get("draft")) or published.get("published_at") is None:
        raise PublishError("Release did not enter the published state")
    _verify_release_metadata(published, metadata, notes)
    _verify_exact_assets(
        repo=repo,
        release=published,
        local_assets=local_assets,
        tag=tag,
        commit=commit,
        signer_workflow=signer_workflow,
    )
    _verify_remote_tag(repo, tag, commit)
    return "published-new" if created else "published-existing-draft"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--notes", required=True, type=Path)
    parser.add_argument("--asset", required=True, action="append", type=Path)
    parser.add_argument("--signer-workflow", required=True)
    args = parser.parse_args()
    try:
        result = publish(
            repo=args.repo,
            tag=args.tag,
            commit=args.commit,
            notes_path=args.notes,
            assets=args.asset,
            signer_workflow=args.signer_workflow,
        )
    except (json.JSONDecodeError, OSError, PublishError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"RELEASE_RESULT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
