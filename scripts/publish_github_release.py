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
from urllib.parse import quote

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


def _api_value(endpoint: str, *arguments: str) -> Any:
    result = _run("api", endpoint, *arguments, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"GitHub API request failed for {endpoint}: {detail}")
    return json.loads(result.stdout)


def _api_json(endpoint: str, *arguments: str) -> dict[str, Any]:
    value = _api_value(endpoint, *arguments)
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


def _object_id(value: dict[str, Any], description: str) -> int:
    identifier = value.get("id")
    if type(identifier) is not int or identifier <= 0:
        raise PublishError(f"{description} has no positive numeric API id")
    return identifier


def _release_by_id(repo: str, release_id: int, tag: str) -> dict[str, Any]:
    release = _api_json(f"repos/{repo}/releases/{release_id}")
    if _object_id(release, "Release") != release_id or release.get("tag_name") != tag:
        raise PublishError("Release id/tag changed during publication")
    return release


def _release(repo: str, tag: str) -> dict[str, Any] | None:
    # The tag endpoint only finds published releases. Authenticated list-releases
    # includes drafts; inspect every page before deciding that this tag is absent.
    seen_ids: set[int] = set()
    matches: list[int] = []
    for page in range(1, 101):
        releases = _api_value(f"repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(releases, list) or len(releases) > 100:
            raise PublishError("GitHub returned a malformed Release page")
        for release in releases:
            if not isinstance(release, dict):
                raise PublishError("GitHub returned a non-object Release entry")
            release_id = _object_id(release, "Release")
            if release_id in seen_ids:
                raise PublishError("Release pagination repeated an API id")
            seen_ids.add(release_id)
            if not isinstance(release.get("tag_name"), str) or type(release.get("draft")) is not bool:
                raise PublishError("GitHub returned malformed Release tag/draft metadata")
            if release["tag_name"] == tag:
                matches.append(release_id)
                if len(matches) > 1:
                    raise PublishError(f"Multiple Releases exist for the exact tag: {tag}")
        if len(releases) < 100:
            break
    else:
        raise PublishError("Release pagination exceeded the 100-page safety limit")
    return _release_by_id(repo, matches[0], tag) if matches else None


def _verify_release_metadata(release: dict[str, Any], metadata: dict[str, Any], notes: str) -> None:
    if type(release.get("draft")) is not bool:
        raise PublishError("Release draft state is not a boolean")
    if release.get("tag_name") != metadata["tag"]:
        raise PublishError("Release tag_name does not match validated source metadata")
    if release.get("name") != metadata["release_title"]:
        raise PublishError(f"Release title mismatch: {release.get('name')!r}")
    if release.get("prerelease") is not False:
        raise PublishError("Stable AegisVault releases must not be marked prerelease")
    if _normalized_markdown(str(release.get("body", ""))) != _normalized_markdown(notes):
        raise PublishError("Release body differs from the committed release notes")


def _asset_map(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    if not isinstance(release.get("assets"), list):
        raise PublishError("Release assets are not a list")
    for asset in release["assets"]:
        if not isinstance(asset, dict):
            raise PublishError("Release contains a non-object asset")
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


def _download_and_verify(repo: str, remote_asset: dict[str, Any], local_path: Path) -> None:
    asset_id = _object_id(remote_asset, "Release asset")
    with tempfile.TemporaryDirectory(prefix="aegisvault-release-download-") as temporary_dir:
        downloaded = Path(temporary_dir) / local_path.name
        with downloaded.open("wb") as destination:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/releases/assets/{asset_id}", "-H", "Accept: application/octet-stream"],
                check=False,
                stdout=destination,
                stderr=subprocess.PIPE,
            )
        if result.returncode != 0:
            raise PublishError(f"Release asset download failed: {result.stderr.decode('utf-8', errors='replace').strip()}")
        if not downloaded.is_file() or _sha256(downloaded) != _sha256(local_path):
            raise PublishError(f"Downloaded Release asset differs from local candidate: {local_path.name}")


def _upload_asset(repo: str, release_id: int, local_path: Path) -> None:
    endpoint = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={quote(local_path.name, safe='')}"
    asset = _api_json(endpoint, "--method", "POST", "--input", str(local_path), "-H", "Content-Type: application/octet-stream")
    if asset.get("name") != local_path.name:
        raise PublishError("Uploaded asset name differs from the requested asset")
    _object_id(asset, "Release asset")
    _verify_asset_metadata(asset, local_path)


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
        _download_and_verify(repo, remote_assets[name], local_path)
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
        _verify_remote_tag(repo, tag, commit)
        release = _api_json(
            f"repos/{repo}/releases", "--method", "POST",
            "-f", f"tag_name={tag}", "-f", f"target_commitish={commit}",
            "-f", f"name={metadata['release_title']}", "-f", f"body={notes}",
            "-F", "draft=true", "-F", "prerelease=false",
        )
        _verify_release_metadata(release, metadata, notes)
        release_id = _object_id(release, "Created draft Release")
        if release["draft"] is not True:
            raise PublishError("Create Release did not return a draft")
        created = True
        release = _release_by_id(repo, release_id, tag)
        if release.get("draft") is not True:
            raise PublishError("New draft changed state before verification")

    _verify_release_metadata(release, metadata, notes)
    release_id = _object_id(release, "Release")
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
        _download_and_verify(repo, remote_asset, local_assets[name])
    for name, local_path in sorted(local_assets.items()):
        if name not in existing_assets:
            _upload_asset(repo, release_id, local_path)

    release = _release_by_id(repo, release_id, tag)
    _verify_release_metadata(release, metadata, notes)
    if release["draft"] is not True:
        raise PublishError("Draft changed state before publication")
    _verify_exact_assets(
        repo=repo,
        release=release,
        local_assets=local_assets,
        tag=tag,
        commit=commit,
        signer_workflow=signer_workflow,
    )
    _verify_remote_tag(repo, tag, commit)
    _api_json(f"repos/{repo}/releases/{release_id}", "--method", "PATCH", "-F", "draft=false")
    published = _release_by_id(repo, release_id, tag)
    if published.get("draft") is not False or published.get("published_at") is None:
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
