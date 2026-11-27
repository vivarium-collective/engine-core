"""Lean, framework-free run-environment capture for reproducibility.

Records the Python + platform + the versions (and git sha, when importable from a
checkout) of the engine packages a wrapper names, so every run can say exactly which
simulator build produced it. No dependency on the investigation framework.
"""
from __future__ import annotations

import platform
import sys
from importlib import metadata


def _git_sha(dist_name: str) -> str:
    try:
        mod = __import__(dist_name.replace("-", "_"))
        import pathlib
        import subprocess
        root = pathlib.Path(getattr(mod, "__file__", "") or "").resolve().parent
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def capture_run_env(packages=()) -> dict:
    """A reproducibility record: python, platform, and {name: {version, git_sha}} for
    each named package. Missing packages are recorded with an empty version rather than
    raising, so capture never breaks a run."""
    pkgs = {}
    for name in packages:
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            version = ""
        pkgs[name] = {"version": version, "git_sha": _git_sha(name)}
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": pkgs,
    }
