"""
Persistent user config: key bindings, sound/autopress preferences, and
last-used selections. Lives outside the repo (in the OS's per-user app
data folder) so `git pull` / the in-app updater never touches it, and
"reset to defaults" is just deleting one file.
"""

import json
import os

from data import STYLES, STYLE_ORDER


def _config_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "RS3Companion")
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_PATH = os.path.join(_config_dir(), "config.json")

DEFAULTS = {
    "sound_on": True,
    "autopress_confirmed": False,  # must be explicitly armed once per session either way
    "last_style": "necromancy",
    "last_boss": "general",
    "last_mode": "revo_basics",  # or "revo_pp"
    "keys": {style: dict(STYLES[style]["keys_default"]) for style in STYLE_ORDER},
}


class AppConfig:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                merged = json.loads(json.dumps(DEFAULTS))  # deep copy
                merged.update({k: v for k, v in loaded.items() if k != "keys"})
                loaded_keys = loaded.get("keys", {})
                for style in STYLE_ORDER:
                    merged["keys"][style].update(loaded_keys.get(style, {}))
                return merged
            except (json.JSONDecodeError, OSError):
                pass
        return json.loads(json.dumps(DEFAULTS))

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def keys_for(self, style_key):
        return self.data["keys"].setdefault(style_key, {})

    def set_key(self, style_key, ability, key):
        self.keys_for(style_key)[ability] = key

    def reset_keys(self, style_key):
        self.data["keys"][style_key] = dict(STYLES[style_key]["keys_default"])
