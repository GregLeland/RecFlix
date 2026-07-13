"""Phase 2: build data/movies.sqlite from the bulk TMDB dump.

Source: alanvourch/tmdb-movies-daily-updates on Kaggle (daily refresh of the
full TMDB catalog joined with IMDb ratings). Downloaded via kagglehub —
anonymous, no API calls.

Keeps every movie that has a title and a poster (the UI renders a poster for
everything). Recommendation lists are added afterward by build_neighbors.py.
"""
import os
import sqlite3
import sys

import kagglehub
import pandas as pd

DB = os.path.join(os.path.dirname(__file__), "..", "data", "movies.sqlite")

USED_COLS = ["id", "imdb_id", "title", "release_date", "status", "genres",
             "overview", "tagline", "cast", "director", "poster_path",
             "popularity", "vote_count", "vote_average", "imdb_rating",
             "runtime", "keywords"]

SCHEMA = """
DROP TABLE IF EXISTS movies;
CREATE TABLE movies (
    tmdb_id INTEGER PRIMARY KEY,
    imdb_id TEXT,
    title TEXT NOT NULL,
    display_title TEXT NOT NULL,   -- "Title (Year)" shown in autocomplete/search
    year INTEGER,
    genres TEXT,
    overview TEXT,
    tagline TEXT,
    cast TEXT,
    director TEXT,
    poster_path TEXT NOT NULL,
    popularity REAL,
    vote_count INTEGER,
    vote_average REAL,
    imdb_rating REAL,
    runtime INTEGER,
    keywords TEXT,
    genre_recs TEXT,   -- JSON list of tmdb_ids, filled by build_neighbors.py
    cast_recs TEXT,
    desc_recs TEXT
);
"""


def main():
    path = kagglehub.dataset_download("alanvourch/tmdb-movies-daily-updates")
    csv_path = os.path.join(path, "TMDB_all_movies.csv")
    print(f"Source: {csv_path}")

    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    total = kept = 0
    for chunk in pd.read_csv(csv_path, usecols=USED_COLS, chunksize=200_000):
        total += len(chunk)
        chunk = chunk.dropna(subset=["title", "poster_path"])
        chunk = chunk[chunk["title"].str.strip() != ""]
        year = pd.to_datetime(chunk["release_date"], errors="coerce").dt.year
        chunk = chunk.assign(
            year=year,
            display_title=chunk["title"].str.strip()
            + year.map(lambda y: "" if pd.isna(y) else f" ({int(y)})"),
        )
        rows = chunk[["id", "imdb_id", "title", "display_title", "year",
                      "genres", "overview", "tagline", "cast", "director",
                      "poster_path", "popularity", "vote_count", "vote_average",
                      "imdb_rating", "runtime", "keywords"]]
        rows = rows.astype(object).where(pd.notna(rows), None)
        con.executemany(
            """INSERT OR IGNORE INTO movies
               (tmdb_id, imdb_id, title, display_title, year, genres, overview,
                tagline, cast, director, poster_path, popularity, vote_count,
                vote_average, imdb_rating, runtime, keywords)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows.itertuples(index=False, name=None),
        )
        kept = con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        print(f"  processed {total:,} rows -> {kept:,} kept")

    print("Creating indexes...")
    con.executescript("""
        CREATE INDEX idx_popularity ON movies(popularity DESC);
        CREATE INDEX idx_display_title ON movies(display_title COLLATE NOCASE);
        CREATE INDEX idx_vote_count ON movies(vote_count);
    """)
    # FTS index for fast substring autocomplete over 1M titles
    con.executescript("""
        DROP TABLE IF EXISTS title_fts;
        CREATE VIRTUAL TABLE title_fts USING fts5(
            display_title, content='movies', content_rowid='tmdb_id',
            tokenize='trigram'
        );
        INSERT INTO title_fts(rowid, display_title)
            SELECT tmdb_id, display_title FROM movies;
    """)
    con.commit()

    n, with_votes, newest = con.execute(
        "SELECT COUNT(*), SUM(vote_count >= 20), MAX(year) FROM movies"
    ).fetchone()
    con.execute("VACUUM")
    con.close()
    size_mb = os.path.getsize(DB) / 1e6
    print(f"\nDone: {n:,} movies ({with_votes:,} with >=20 votes), newest year {newest}")
    print(f"{os.path.normpath(DB)}: {size_mb:.0f} MB")


if __name__ == "__main__":
    main()
