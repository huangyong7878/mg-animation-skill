"""Local MG Studio settings. Secrets live in macOS Keychain, never JSON."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

SERVICE = "mg-animation-skill.studio.deepseek"
ACCOUNT = "api-key"
DEFAULT = {"r5_enabled": False, "proxy_mode": "system", "proxy_url": ""}
VALID_MODES = {"system", "custom", "none"}

def settings_path(repo):
    return Path(repo).resolve() / "work/mg_studio/settings.json"

def _security(*args, input_text=None):
    if sys.platform != "darwin":
        raise RuntimeError("macOS Keychain required for credential management")
    return subprocess.run(["security", *args], input=input_text, text=True,
                          capture_output=True, timeout=15, check=False)

def has_key():
    result = _security("find-generic-password", "-a", ACCOUNT, "-s", SERVICE, "-w")
    return result.returncode == 0 and bool(result.stdout.strip())

def get_key():
    result = _security("find-generic-password", "-a", ACCOUNT, "-s", SERVICE, "-w")
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("DeepSeek API Key not found in macOS Keychain")
    return result.stdout.strip()

def save_key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 512 or "\n" in value or "\r" in value:
        raise ValueError("Invalid API Key")
    # -w without a value reads the password from stdin. Never place key in argv/logs.
    result = _security("add-generic-password", "-a", ACCOUNT, "-s", SERVICE,
                       "-U", "-w", input_text=value.strip()+"\n")
    if result.returncode:
        raise RuntimeError("Keychain failed to store the credential")

def delete_key():
    result = _security("delete-generic-password", "-a", ACCOUNT, "-s", SERVICE)
    if result.returncode:
        raise RuntimeError("Keychain credential deletion failed")

def validate(value):
    if not isinstance(value, dict):
        raise ValueError("Settings must be an object")
    if set(value) != set(DEFAULT):
        raise ValueError("Unknown or missing settings fields")
    if not isinstance(value["r5_enabled"], bool) or value["proxy_mode"] not in VALID_MODES:
        raise ValueError("Invalid R5 settings")
    url = value["proxy_url"]
    if not isinstance(url, str) or len(url) > 256:
        raise ValueError("Invalid proxy URL")
    if value["proxy_mode"] == "custom":
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError("Custom proxy must be http(s)://host:port without credentials")
        if parts.port is None:
            raise ValueError("Custom proxy requires port")
    elif url:
        raise ValueError("Proxy URL only allowed in custom mode")
    return value

def load(repo):
    path = settings_path(repo)
    if not path.exists():
        return dict(DEFAULT)
    return validate(json.loads(path.read_text(encoding="utf-8")))

def save(repo, data):
    data = validate(data)
    path = settings_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

def public_status(repo):
    return {**load(repo), "deepseek_key_configured": has_key() if sys.platform == "darwin" else False,
            "key_storage": "macOS Keychain"}
