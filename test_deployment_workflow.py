"""Release connection failures must never mutate production."""
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def release(tmp_path):
    root = Path(__file__).parent
    key = tmp_path / "test_identity"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    public = key.with_suffix(".pub").read_text().split()[1]
    digest = hashlib.sha256(base64.b64decode(public)).hexdigest()
    path = tmp_path / "deploy" / "github_release.sh"
    path.parent.mkdir()
    source = (root / "deploy/github_release.sh").read_text()
    source = source.replace("trusted_host_digest=81647e644f59cd3f4485129bc7695536eb0bd5e6bd4ce55b492c0df163f83d22", "trusted_host_digest=" + digest)
    path.write_text(source)
    (path.parent / "production_release.sh").write_text("#!/bin/sh\nexit 0\n")
    scan = tmp_path / "scan"
    scan.write_text("209.38.93.248 ssh-ed25519 " + public + "\n")
    calls = tmp_path / "calls"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in {
        "ssh-keyscan": 'cat "$TEST_SCAN"',
        "ssh": 'echo "ssh $*" >> "$TEST_CALLS"; exit "${TEST_SSH_STATUS:-0}"',
        "scp": 'echo "scp $*" >> "$TEST_CALLS"',
        "git": 'printf "%s\\trefs/heads/main\\n" "$TEST_MAIN"',
    }.items():
        executable = bindir / name
        executable.write_text("#!/bin/sh\n" + body + "\n")
        executable.chmod(0o700)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"], SERVER_KEY=key.read_text(), TEST_SCAN=str(scan), TEST_CALLS=str(calls), TEST_MAIN="a" * 40)
    env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "test-summary.md")
    # The script needs Python 3, not the host's optional shell alias.
    (bindir / "python3").symlink_to(sys.executable)
    return path, env, calls, scan


def run_release(release, mode="verify", **changes):
    path, env, calls, scan = release
    result = subprocess.run(["bash", str(path), mode, "a" * 40], env=dict(env, **changes), text=True, capture_output=True)
    return result, calls.read_text() if calls.exists() else ""


def test_missing_or_invalid_credential_never_connects(release):
    for key in ("", "invalid-private-key-sentinel"):
        result, calls = run_release(release, SERVER_KEY=key)
        assert result.returncode != 0
        assert not calls
        assert "invalid-private-key-sentinel" not in result.stdout + result.stderr


def test_untrusted_host_never_authenticates(release):
    release[3].write_text("209.38.93.248 ssh-ed25519 " + base64.b64encode(b"untrusted").decode() + "\n")
    result, calls = run_release(release)
    assert result.returncode != 0
    assert "host identity differs" in result.stderr
    assert not calls


def test_rejected_identity_never_uploads_or_deploys(release):
    result, calls = run_release(release, "deploy", TEST_SSH_STATUS="255")
    assert result.returncode != 0
    assert "SSH authentication failed" in result.stdout
    assert calls.count("ssh ") == 1
    assert "scp " not in calls
    assert "BatchMode=yes" in calls and "IdentitiesOnly=yes" in calls
    assert "StrictHostKeyChecking=yes" in calls and "PasswordAuthentication=no" in calls


def test_verify_is_read_only_and_old_releases_are_skipped(release):
    result, calls = run_release(release)
    assert result.returncode == 0
    assert calls.count("ssh ") == 2 and "scp " not in calls
    release[2].unlink()
    result, calls = run_release(release, "deploy", TEST_MAIN="b" * 40)
    assert result.returncode == 0
    assert "Superseded commit" in result.stdout
    assert calls.count("ssh ") == 1 and "scp " not in calls
