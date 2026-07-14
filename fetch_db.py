"""Dataset fetch for hosting.

ensure_db() makes sure the SQLite catalog exists at RECFLIX_DB, streaming it
from RECFLIX_DB_URL (a GitHub Release asset) if missing — e.g. onto a fresh
Railway volume. Called from the start command before gunicorn, and again
defensively at engine import; a no-op when the file already exists.
"""
import os
import sys
import urllib.request

DB_PATH = os.environ.get("RECFLIX_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "movies.sqlite")


def ensure_db():
    if os.path.exists(DB_PATH):
        print(f"[fetch_db] {DB_PATH} present ({os.path.getsize(DB_PATH)/1e6:.0f} MB)")
        return DB_PATH
    url = os.environ.get("RECFLIX_DB_URL")
    if not url:
        raise RuntimeError(
            f"[fetch_db] {DB_PATH} is missing and RECFLIX_DB_URL is not set. "
            "Set RECFLIX_DB_URL to the movies.sqlite release asset URL, and "
            "make sure the volume is mounted at the directory in RECFLIX_DB.")
    parent = os.path.dirname(DB_PATH)
    if parent and not os.path.isdir(parent):
        raise RuntimeError(
            f"[fetch_db] directory {parent} does not exist — is the Railway "
            f"volume attached and mounted there?")
    tmp = DB_PATH + ".part"
    print(f"[fetch_db] downloading {url} ...")
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(tmp, DB_PATH)
    print(f"[fetch_db] done: {os.path.getsize(DB_PATH)/1e6:.0f} MB")
    return DB_PATH


if __name__ == "__main__":
    try:
        ensure_db()
    except RuntimeError as e:
        sys.exit(str(e))
