"""
In-app updater: compares the local VERSION file against the latest
GitHub release, and if this is a git checkout, applies the update with
a fast-forward-only pull (never touches uncommitted local changes).
"""

import json
import os
import subprocess
import urllib.request
import urllib.error

REPO = "bburge14/RS3Helper"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(APP_DIR, "VERSION")


def local_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def latest_release():
    """Returns (tag, url, notes) for the latest GitHub release, or a
    (None, None, message) tuple describing why it couldn't be fetched."""
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.load(resp)
        return payload["tag_name"], payload["html_url"], payload.get("body", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None, "No releases found (or the repo is still private)."
        return None, None, f"GitHub returned an error ({e.code})."
    except urllib.error.URLError:
        return None, None, "Couldn't reach GitHub — check your connection."
    except Exception:
        return None, None, "Unexpected error checking for updates."


def repo_root():
    """Walk up from this file looking for a .git directory. Returns the
    path, or None if this isn't inside a git checkout (e.g. a bare zip
    download)."""
    d = APP_DIR
    for _ in range(6):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def is_git_checkout():
    return repo_root() is not None


def working_tree_dirty(root):
    result = subprocess.run(
        ["git", "-C", root, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def apply_git_update():
    """Fast-forward pulls origin/main. Returns (ok, message)."""
    root = repo_root()
    if not root:
        return False, "Not a git checkout — download the latest release zip instead."
    if working_tree_dirty(root):
        return False, ("You have local changes in the repo. Commit, discard, "
                        "or stash them, then try again.")
    fetch = subprocess.run(["git", "-C", root, "fetch", "origin", "--quiet"],
                            capture_output=True, text=True)
    if fetch.returncode != 0:
        return False, f"git fetch failed: {fetch.stderr.strip()}"
    pull = subprocess.run(
        ["git", "-C", root, "pull", "--ff-only", "origin", "main"],
        capture_output=True, text=True,
    )
    if pull.returncode != 0:
        return False, f"git pull failed: {pull.stderr.strip()}"
    return True, "Updated. Restart the app to pick up the changes."
