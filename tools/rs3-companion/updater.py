"""
Updater: compares the local VERSION file against the latest GitHub
release and applies it automatically.

- Git checkout: fast-forward-only `git pull` (never touches uncommitted
  local changes -- silently skips if the tree is dirty).
- Zip install (no .git found): downloads the release's zip asset and
  overwrites this app's own files in place.

Either way, applying an update only changes files on disk -- the
already-running process keeps executing the code it loaded at startup,
so the caller is responsible for prompting a restart once `auto_update()`
reports success.
"""

import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

REPO = "bburge14/RS3Helper"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(APP_DIR, "VERSION")
APP_ENTRY = os.path.join(APP_DIR, "app.py")
# Optional, gitignored: a fine-grained PAT scoped read-only to just this
# repo, needed only if the repo is private. Never committed, never
# distributed -- see README "Private repo + auto-update" for setup.
TOKEN_FILE = os.path.join(APP_DIR, ".github_token")


def local_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def _versions_match(tag, local):
    return tag.lstrip("v") == local.lstrip("v")


def _load_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            tok = f.read().strip()
            return tok or None
    except OSError:
        return None


def _auth_headers(accept="application/vnd.github+json"):
    headers = {"Accept": accept}
    tok = _load_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers


def get_release_payload():
    """Returns (payload_dict, error_message). error_message is None on
    success. Uses a local token (see _load_token) if present -- required
    to see releases at all once the repo is private."""
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    req = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            if _load_token():
                return None, "No releases found (or the token can't see this repo)."
            return None, ("No releases found -- if the repo is private, add a token: "
                           "see README \"Private repo + auto-update\".")
        if e.code == 401:
            return None, "GitHub rejected the token in .github_token (expired/revoked?)."
        return None, f"GitHub returned an error ({e.code})."
    except urllib.error.URLError:
        return None, "Couldn't reach GitHub — check your connection."
    except Exception:
        return None, "Unexpected error checking for updates."


def latest_release():
    """Returns (tag, url, notes) for the latest GitHub release, or a
    (None, None, message) tuple describing why it couldn't be fetched.
    Kept as a stable, simple entry point for the Settings tab's manual
    "Check for updates" button."""
    payload, err = get_release_payload()
    if payload is None:
        return None, None, err
    return payload["tag_name"], payload["html_url"], payload.get("body", "")


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
    return True, "Updated. Restart to apply."


def _find_zip_asset(payload):
    """Returns (asset_id, browser_download_url) or (None, None)."""
    for asset in payload.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("rs3-companion-") and name.endswith(".zip"):
            return asset.get("id"), asset.get("browser_download_url")
    return None, None


def apply_zip_update(payload):
    """Downloads the release's rs3-companion zip asset and overwrites
    this app's own files in place (everything under tools/rs3-companion/
    in the archive). Returns (ok, message)."""
    asset_id, browser_url = _find_zip_asset(payload)
    if not asset_id:
        return False, "This release has no rs3-companion zip asset."

    tok = _load_token()
    if tok:
        # Private (or token-gated) repos: the plain browser_download_url
        # redirects to a signed storage URL that doesn't accept our auth
        # header, so fetch the binary through the API's asset endpoint
        # instead, which does.
        url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}"
        req = urllib.request.Request(url, headers=_auth_headers("application/octet-stream"))
    else:
        req = urllib.request.Request(browser_url)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        return False, f"Download failed: {e}"

    prefix = "tools/rs3-companion/"
    written = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if info.is_dir() or not name.startswith(prefix):
                    continue
                rel_parts = name[len(prefix):].split("/")
                if not rel_parts or not rel_parts[-1]:
                    continue
                dest = os.path.join(APP_DIR, *rel_parts)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as out:
                    out.write(src.read())
                written += 1
    except zipfile.BadZipFile:
        return False, "Downloaded file wasn't a valid zip."

    if written == 0:
        return False, "Zip didn't contain the expected files."

    req_path = os.path.join(APP_DIR, "requirements.txt")
    if os.path.exists(req_path):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path, "--quiet"],
                        capture_output=True, text=True)

    return True, "Updated. Restart to apply."


def auto_update():
    """Checks the latest release and applies it (git pull or zip
    overwrite, whichever fits how this copy was installed) if it's
    newer than the local VERSION. Returns one of:
      ("up_to_date", local_version, None)
      ("updated", new_tag, message)
      ("failed", new_tag_or_None, message)
      ("error", None, message)          -- couldn't even check
    Safe to call from a background thread -- does no GUI work itself.
    """
    payload, err = get_release_payload()
    if payload is None:
        return "error", None, err

    tag = payload["tag_name"]
    local = local_version()
    if _versions_match(tag, local):
        return "up_to_date", local, None

    if is_git_checkout():
        ok, msg = apply_git_update()
    else:
        ok, msg = apply_zip_update(payload)

    return ("updated" if ok else "failed"), tag, msg


def relaunch_and_exit():
    """Spawns a fresh copy of the app pointed at the (now updated) files
    on disk, then exits this process. Caller should save/close first."""
    try:
        subprocess.Popen([sys.executable, APP_ENTRY], cwd=APP_DIR)
    except Exception:
        pass
    os._exit(0)
