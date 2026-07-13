"""Rebuild the RecFlix movie dataset from the TMDB API.

Reads the movie list (titles + tmdbIds) from data/moovees.json — the 2019
snapshot of the old ClearDB movies table — and refreshes everything that goes
stale from TMDB: poster paths, plot descriptions, and top-billed cast.
Writes the result to data/movies.csv, which the app loads at startup instead
of a database.

Re-run this any time TMDB reshuffles their image paths:
    python scripts/build_dataset.py
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api_key import api_key

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SOURCE = os.path.join(DATA_DIR, "moovees.json")
DEST = os.path.join(DATA_DIR, "movies.csv")
CAST_SIZE = 6  # matches the original database's top-billed cast depth
WORKERS = 20

session = requests.Session()


def fetch_movie(tmdb_id):
    """One call gets details + credits together via append_to_response."""
    url = (f"https://api.themoviedb.org/3/movie/{tmdb_id}"
           f"?api_key={api_key}&append_to_response=credits")
    for attempt in range(4):
        resp = session.get(url, timeout=20)
        if resp.status_code == 429:
            time.sleep(float(resp.headers.get("Retry-After", 2)) + 0.5)
            continue
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"tmdbId {tmdb_id}: rate-limited after retries")


def main():
    with open(SOURCE, encoding="utf-8") as f:
        src = json.load(f)

    keys = list(src["tmdbId"].keys())
    print(f"Source snapshot: {len(keys)} movies. Fetching from TMDB...")

    rows, gone, no_poster = [], [], []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_movie, src["tmdbId"][k]): k for k in keys}
        for i, fut in enumerate(as_completed(futures), 1):
            k = futures[fut]
            data = fut.result()
            title = src["title"][k]
            if data is None:
                gone.append(title)
                continue
            if not data.get("poster_path"):
                no_poster.append(title)
                continue
            cast = [c["name"] for c in data.get("credits", {}).get("cast", [])[:CAST_SIZE]]
            rows.append({
                "movie_id": src["movie_id"][k],
                "title": title,
                "genres": src["genres"][k],
                "imdbId": src["imdbId"][k],
                "poster_path": data["poster_path"],
                "tmdbId": src["tmdbId"][k],
                "movie_descriptions": data.get("overview") or "",
                # stored as a stringified list, same format as the old database
                "cast": str(cast),
            })
            if i % 500 == 0:
                print(f"  {i}/{len(keys)} fetched...")

    # the app looks movies up by title, so titles must be unique
    rows.sort(key=lambda r: r["movie_id"])
    seen, deduped = set(), []
    for r in rows:
        if r["title"] in seen:
            continue
        seen.add(r["title"])
        deduped.append(r)

    with open(DEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(deduped[0].keys()))
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nWrote {len(deduped)} movies to {os.path.normpath(DEST)}")
    print(f"Dropped: {len(gone)} no longer on TMDB, {len(no_poster)} without a poster, "
          f"{len(rows) - len(deduped)} duplicate titles")
    if gone:
        print("  Gone:", ", ".join(gone[:10]) + ("..." if len(gone) > 10 else ""))
    if no_poster:
        print("  No poster:", ", ".join(no_poster[:10]) + ("..." if len(no_poster) > 10 else ""))


if __name__ == "__main__":
    main()
