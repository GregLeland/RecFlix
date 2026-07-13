# Data access layer for the 923k-movie SQLite catalog.
#
# All the machine learning happens offline in scripts/build_neighbors.py;
# at runtime every page is a handful of indexed lookups, so the app runs in
# ~100MB of RAM no matter how big the catalog gets.
import json
import os
import sqlite3
import threading

from rapidfuzz import process as fuzz_process

DB_PATH = os.environ.get(
    "RECFLIX_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "movies.sqlite"),
)

_local = threading.local()


def _con():
    if not hasattr(_local, "con"):
        _local.con = sqlite3.connect(DB_PATH)
        _local.con.row_factory = sqlite3.Row
    return _local.con


# In-memory fuzzy-search pool: display titles of every movie popular enough to
# be worth suggesting on a misspelling (~63k rows, a few MB). Substring
# matches still search the FULL 923k catalog via the FTS index.
_pool_titles = []
_pool_ids = []
for _r in sqlite3.connect(DB_PATH).execute(
    "SELECT display_title, tmdb_id FROM movies WHERE vote_count >= 20"
):
    _pool_titles.append(_r[0])
    _pool_ids.append(_r[1])


def get_movie(tmdb_id):
    return _con().execute(
        "SELECT * FROM movies WHERE tmdb_id = ?", (tmdb_id,)
    ).fetchone()


def random_movies(n=6):
    """Random well-known movies for the homepage grid."""
    return _con().execute(
        "SELECT tmdb_id, poster_path FROM movies WHERE vote_count >= 1000 "
        "ORDER BY RANDOM() LIMIT ?", (n,)
    ).fetchall()


def _fts_quote(term):
    return '"' + term.replace('"', '""') + '"'


def autocomplete(term, limit=20):
    """Popularity-ranked title suggestions; substring match over all 923k titles."""
    term = (term or "").strip()
    if len(term) < 2:
        return []
    if len(term) < 3:  # trigram FTS needs 3+ chars; use prefix match below that
        rows = _con().execute(
            "SELECT display_title FROM movies WHERE display_title LIKE ? "
            "ORDER BY popularity DESC LIMIT ?", (term + "%", limit),
        ).fetchall()
    else:
        rows = _con().execute(
            "SELECT m.display_title FROM title_fts f "
            "JOIN movies m ON m.tmdb_id = f.rowid "
            "WHERE title_fts MATCH ? ORDER BY m.popularity DESC LIMIT ?",
            (_fts_quote(term), limit),
        ).fetchall()
    return [r[0] for r in rows]


def resolve_title(text):
    """tmdb_id for an exactly-typed display title (most popular on collision)."""
    row = _con().execute(
        "SELECT tmdb_id FROM movies WHERE display_title = ? COLLATE NOCASE "
        "ORDER BY popularity DESC LIMIT 1", (text.strip(),),
    ).fetchone()
    return row["tmdb_id"] if row else None


def search(term, limit=5):
    """Fuzzy search: exact substring hits over the full catalog first, then
    rapidfuzz over the popular pool to catch misspellings. Returns
    [(tmdb_id, display_title, score)]."""
    results, seen = [], set()
    for title in autocomplete(term, limit):
        mid = resolve_title(title)
        if mid and mid not in seen:
            seen.add(mid)
            results.append((mid, title, 100))
    if len(results) < limit:
        for title, score, i in fuzz_process.extract(
            term, _pool_titles, limit=limit * 2, score_cutoff=55
        ):
            mid = _pool_ids[i]
            if mid not in seen:
                seen.add(mid)
                results.append((mid, title, round(score)))
            if len(results) >= limit:
                break
    return results[:limit]


def recommendations(tmdb_id, per_dim=12):
    """Three lists of (tmdb_id, poster_path), one per dimension, each per_dim
    long, from the precomputed neighbor lists. Dimensions that came up empty
    at build time (e.g. no plot text) are backfilled from the other lists."""
    movie = get_movie(tmdb_id)
    if movie is None:
        return None
    dims = []
    for col in ("genre_recs", "cast_recs", "desc_recs"):
        ids = json.loads(movie[col] or "[]")
        dims.append([i for i in ids if i != tmdb_id])
    backfill = [i for ids in dims for i in ids]
    filled = []
    for ids in dims:
        ids = list(ids)
        for candidate in backfill:
            if len(ids) >= per_dim:
                break
            if candidate not in ids:
                ids.append(candidate)
        filled.append(ids[:per_dim])

    wanted = {i for ids in filled for i in ids}
    posters = dict(_con().execute(
        f"SELECT tmdb_id, poster_path FROM movies "
        f"WHERE tmdb_id IN ({','.join('?' * len(wanted))})", list(wanted),
    ).fetchall()) if wanted else {}
    return [[(i, posters.get(i, "")) for i in ids] for ids in filled]
