"""Boot-time dataset fetch for hosting.

If the SQLite catalog isn't at RECFLIX_DB yet (fresh Railway volume), stream
it from RECFLIX_DB_URL (a GitHub Release asset). Runs before gunicorn in the
Procfile; a no-op when the file already exists.
"""
import os
import sys
import urllib.request

db_path = os.environ.get("RECFLIX_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "movies.sqlite")
url = os.environ.get("RECFLIX_DB_URL")

if os.path.exists(db_path):
    print(f"[fetch_db] {db_path} present ({os.path.getsize(db_path)/1e6:.0f} MB)")
    sys.exit(0)
if not url:
    sys.exit(f"[fetch_db] {db_path} missing and RECFLIX_DB_URL not set")

os.makedirs(os.path.dirname(db_path), exist_ok=True)
tmp = db_path + ".part"
print(f"[fetch_db] downloading {url} ...")
with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
    while chunk := r.read(1 << 20):
        f.write(chunk)
os.replace(tmp, db_path)
print(f"[fetch_db] done: {os.path.getsize(db_path)/1e6:.0f} MB")
