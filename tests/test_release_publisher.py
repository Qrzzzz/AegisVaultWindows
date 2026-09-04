from __future__ import annotations

import copy
import importlib
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = "owner/repo"
TAG = "v1.0.0"
COMMIT = "a" * 40
WORKFLOW = f"{REPO}/.github/workflows/release.yml"


@pytest.fixture
def publisher(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = importlib.import_module("publish_github_release")
    # Every test must supply explicit mocks; none may reach gh or a remote object.
    monkeypatch.setattr(module, "_run", lambda *_args, **_kwargs: pytest.fail("unexpected gh call"))
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("unexpected subprocess"))
    return module


def _record(identifier: int = 42, *, tag: str = TAG, draft: bool = True) -> dict[str, Any]:
    return {
        "id": identifier,
        "tag_name": tag,
        "name": "AegisVault v1.0.0",
        "body": "Complete release notes.\n",
        "draft": draft,
        "prerelease": False,
        "published_at": None if draft else "2026-09-04T00:00:00Z",
        "assets": [],
    }


def _asset(module: ModuleType, path: Path, identifier: int) -> dict[str, Any]:
    return {
        "id": identifier,
        "name": path.name,
        "state": "uploaded",
        "size": path.stat().st_size,
        "digest": f"sha256:{module._sha256(path)}",
    }


def test_tag_endpoint_404_does_not_hide_an_existing_draft(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    draft = _record()

    def run(*args: str, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args[1])
        if "/releases/tags/" in args[1]:
            return subprocess.CompletedProcess(args, 1, "", "HTTP 404: Not Found")
        response: Any = [draft] if "?per_page=" in args[1] else draft
        return subprocess.CompletedProcess(args, 0, json.dumps(response), "")

    monkeypatch.setattr(publisher, "_run", run)
    assert publisher._release(REPO, TAG) == draft
    assert calls == [f"repos/{REPO}/releases?per_page=100&page=1", f"repos/{REPO}/releases/42"]


def test_draft_on_a_later_page_is_discovered(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    first = [_record(index, tag=f"v0.0.{index}", draft=False) for index in range(1, 101)]
    draft = _record(900)
    responses = {
        f"repos/{REPO}/releases?per_page=100&page=1": first,
        f"repos/{REPO}/releases?per_page=100&page=2": [draft],
        f"repos/{REPO}/releases/900": draft,
    }
    calls = []

    def value(endpoint: str, *_args: str) -> Any:
        calls.append(endpoint)
        return responses[endpoint]

    monkeypatch.setattr(publisher, "_api_value", value)
    assert publisher._release(REPO, TAG)["id"] == 900
    assert calls == list(responses)


def test_duplicate_exact_tag_is_rejected(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publisher, "_api_value", lambda *_: [_record(41, draft=False), _record(42)])
    with pytest.raises(publisher.PublishError, match="Multiple Releases"):
        publisher._release(REPO, TAG)


@pytest.mark.parametrize("page", [{"message": "not a list"}, [None], [{"id": True}], [{"id": 1, "tag_name": TAG, "draft": "true"}]])
def test_malformed_release_pages_fail_closed(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, page: Any) -> None:
    monkeypatch.setattr(publisher, "_api_value", lambda *_: page)
    with pytest.raises(publisher.PublishError):
        publisher._release(REPO, TAG)


def test_repeated_page_is_rejected(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    page = [_record(index, tag=f"v0.0.{index}") for index in range(1, 101)]
    monkeypatch.setattr(publisher, "_api_value", lambda *_: page)
    with pytest.raises(publisher.PublishError, match="repeated an API id"):
        publisher._release(REPO, TAG)


def test_list_api_404_is_not_treated_as_absence(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publisher, "_run", lambda *args, **_: subprocess.CompletedProcess(args, 1, "", "HTTP 404: Not Found"))
    with pytest.raises(publisher.PublishError, match="HTTP 404"):
        publisher._release(REPO, TAG)


def test_exact_id_read_rejects_changed_identity(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publisher, "_api_json", lambda *_: _record(99))
    with pytest.raises(publisher.PublishError, match="id/tag changed"):
        publisher._release_by_id(REPO, 42, TAG)


@pytest.fixture
def candidate(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    names = [f"AegisVault-{TAG}-win64.zip", f"AegisVault-{TAG}.cdx.json", "SHA256SUMS"]
    metadata = {"tag": TAG, "release_title": "AegisVault v1.0.0", "public_assets": names}
    notes = tmp_path / "notes.md"
    notes.write_text("Complete release notes.\n", encoding="utf-8")
    assets = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        assets.append(path)
    monkeypatch.setattr(publisher, "load_release_metadata", lambda **_: metadata)
    monkeypatch.setattr(publisher, "_verify_remote_tag", lambda *_: None)
    return {"repo": REPO, "tag": TAG, "commit": COMMIT, "notes_path": notes, "assets": assets, "signer_workflow": WORKFLOW}


@pytest.mark.parametrize("existing_count", [None, 1])
def test_create_and_resume_use_exact_id_until_published(
    publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, candidate: dict[str, Any], existing_count: int | None,
) -> None:
    state = _record()
    state["assets"] = [_asset(publisher, path, 100 + index) for index, path in enumerate(candidate["assets"][:existing_count or 0])]
    monkeypatch.setattr(publisher, "_release", lambda *_: None if existing_count is None else copy.deepcopy(state))
    events: list[tuple[Any, ...]] = []

    def api(endpoint: str, *args: str) -> dict[str, Any]:
        method = args[args.index("--method") + 1] if "--method" in args else "GET"
        events.append((method, endpoint))
        if method == "POST":
            assert endpoint == f"repos/{REPO}/releases"
            assert "draft=true" in args and "prerelease=false" in args
            assert f"target_commitish={COMMIT}" in args
            assert "body=Complete release notes.\n" in args
        else:
            assert endpoint == f"repos/{REPO}/releases/42"
        if method == "PATCH":
            assert len([event for event in events if event[0] == "attestation"]) == 3
            assert "draft=false" in args
            state["draft"] = False
            state["published_at"] = "2026-09-04T00:00:00Z"
        return copy.deepcopy(state)

    def upload(_repo: str, release_id: int, path: Path) -> None:
        assert release_id == 42
        events.append(("upload", release_id, path.name))
        state["assets"].append(_asset(publisher, path, 100 + len(state["assets"])))

    monkeypatch.setattr(publisher, "_api_json", api)
    monkeypatch.setattr(publisher, "_upload_asset", upload)
    monkeypatch.setattr(publisher, "_download_and_verify", lambda _repo, asset, _path: events.append(("download", asset["id"])))
    monkeypatch.setattr(publisher, "_verify_attestation", lambda *_args: events.append(("attestation",)))
    expected = "published-new" if existing_count is None else "published-existing-draft"
    assert publisher.publish(**candidate) == expected
    assert len([event for event in events if event[0] == "upload"]) == 3 - (existing_count or 0)
    assert len([event for event in events if event[0] == "PATCH"]) == 1
    if existing_count is None:
        assert events[:2] == [("POST", f"repos/{REPO}/releases"), ("GET", f"repos/{REPO}/releases/42")]


def test_published_release_verifies_assets_without_mutation(
    publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, candidate: dict[str, Any],
) -> None:
    release = _record(draft=False)
    release["assets"] = [_asset(publisher, path, index + 100) for index, path in enumerate(candidate["assets"])]
    monkeypatch.setattr(publisher, "_release", lambda *_: release)
    checked = []
    monkeypatch.setattr(publisher, "_download_and_verify", lambda _repo, asset, _path: checked.append(asset["id"]))
    monkeypatch.setattr(publisher, "_verify_attestation", lambda *_: None)
    assert publisher.publish(**candidate) == "published-idempotent"
    assert sorted(checked) == [100, 101, 102]


@pytest.mark.parametrize("draft", [False, True])
def test_wrong_notes_fail_before_mutation(
    publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, candidate: dict[str, Any], draft: bool,
) -> None:
    release = _record(draft=draft)
    release["body"] = "Different notes"
    monkeypatch.setattr(publisher, "_release", lambda *_: release)
    with pytest.raises(publisher.PublishError, match="body differs"):
        publisher.publish(**candidate)


@pytest.mark.parametrize("draft", [False, True])
def test_wrong_assets_fail_before_mutation(
    publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, candidate: dict[str, Any], draft: bool,
) -> None:
    release = _record(draft=draft)
    release["assets"] = [{"id": 100, "name": "unexpected.zip"}]
    monkeypatch.setattr(publisher, "_release", lambda *_: release)
    with pytest.raises(publisher.PublishError, match="asset"):
        publisher.publish(**candidate)


def test_wrong_api_digest_fails_closed(publisher: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "asset.zip"
    path.write_bytes(b"expected")
    asset = _asset(publisher, path, 100)
    asset["digest"] = "sha256:" + "0" * 64
    with pytest.raises(publisher.PublishError, match="digest mismatch"):
        publisher._verify_asset_metadata(asset, path)


def test_download_by_asset_id_still_checks_actual_bytes(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "asset.zip"
    path.write_bytes(b"expected")

    def download(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert args == ["gh", "api", f"repos/{REPO}/releases/assets/100", "-H", "Accept: application/octet-stream"]
        kwargs["stdout"].write(b"mismatch")
        return subprocess.CompletedProcess(args, 0, None, b"")

    monkeypatch.setattr(publisher.subprocess, "run", download)
    with pytest.raises(publisher.PublishError, match="differs from local candidate"):
        publisher._download_and_verify(REPO, {"id": 100}, path)


def test_upload_uses_release_id_and_never_clobbers(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "asset name.zip"
    path.write_bytes(b"expected")
    calls = []

    def api(endpoint: str, *args: str) -> dict[str, Any]:
        calls.append((endpoint, args))
        return _asset(publisher, path, 100)

    monkeypatch.setattr(publisher, "_api_json", api)
    publisher._upload_asset(REPO, 42, path)
    endpoint, args = calls[0]
    assert endpoint == f"https://uploads.github.com/repos/{REPO}/releases/42/assets?name=asset%20name.zip"
    assert args[:2] == ("--method", "POST")
    assert "--input" in args and str(path) in args
    assert not any("clobber" in arg for arg in args)


def test_attestation_keeps_all_source_and_signer_constraints(publisher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []

    def run(*args: str, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "[]", "")

    monkeypatch.setattr(publisher, "_run", run)
    publisher._verify_attestation(REPO, TAG, COMMIT, WORKFLOW, tmp_path / "asset.zip")
    args = calls[0]
    for flag, value in (("--repo", REPO), ("--signer-workflow", WORKFLOW), ("--signer-digest", COMMIT), ("--source-ref", f"refs/tags/{TAG}"), ("--source-digest", COMMIT)):
        assert args[args.index(flag) + 1] == value
    assert "--deny-self-hosted-runners" in args
