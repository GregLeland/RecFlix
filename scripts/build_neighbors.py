"""Phase 3: precompute per-movie recommendation lists into movies.sqlite.

For each of the three dimensions the site shows (genre, cast, plot), computes
EXACT sparse TF-IDF cosine similarity between every movie and the candidate
pool via chunked sparse matrix multiplication, and stores each movie's top
neighbors as JSON in genre_recs / cast_recs / desc_recs.

No dimensionality reduction: actor names and distinctive plot words are rare
tokens, and exact sparse cosine is what makes "same cast" actually mean same
cast. (An earlier SVD-based version produced noise for exactly that reason.)

Every movie gets recommendations, but only movies with >= MIN_VOTES votes can
BE recommended — keeps zero-vote obscurities out of the rec rows while still
giving them their own working /rec/ page.

Run after build_catalog.py:  python scripts/build_neighbors.py
"""
import json
import os
import re
import sqlite3
import time

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

DB = os.path.join(os.path.dirname(__file__), "..", "data", "movies.sqlite")
MIN_VOTES = 20      # candidate pool: movies allowed to appear as recommendations
TOP_K = 20          # stored per dimension (site shows 12)
CHUNK = 5_000
POP_BLEND = 0.10    # genre dim only: popularity tiebreak among identical genre sets


def phrase_tokens(value, sep):
    """'Tom Hanks, Tim Allen' -> 'tom_hanks tim_allen' so names/phrases are single tokens."""
    if not value:
        return ""
    parts = [re.sub(r"\s+", "_", p.strip().lower()) for p in value.split(sep)]
    return " ".join(p for p in parts if p)


def build_dim(name, texts, pool_mask, pop_score, con, ids, blend_pop, vectorizer_kwargs):
    t0 = time.time()
    print(f"[{name}] vectorizing {len(texts):,} docs...")
    tf = TfidfVectorizer(sublinear_tf=True, **vectorizer_kwargs)
    X = csr_matrix(tf.fit_transform(texts), dtype=np.float32)
    nonempty = np.asarray(X.getnnz(axis=1)).ravel() > 0
    pool = np.where(pool_mask & nonempty)[0]
    pool_ids = ids[pool]
    pool_pop = pop_score[pool]
    P = X[pool].T.tocsr()
    print(f"[{name}] {X.shape[1]:,} features, pool {len(pool):,}; exact cosine search...")

    updates = []
    for start in range(0, X.shape[0], CHUNK):
        S = (X[start:start + CHUNK] @ P).tocsr()  # exact cosine (rows are L2-normalized)
        for row in range(S.shape[0]):
            i = start + row
            if not nonempty[i]:
                updates.append((json.dumps([]), int(ids[i])))
                continue
            lo, hi = S.indptr[row], S.indptr[row + 1]
            cols, sims = S.indices[lo:hi], S.data[lo:hi]
            if blend_pop:
                score = (1 - POP_BLEND) * sims + POP_BLEND * pool_pop[cols]
            else:
                score = sims + 1e-6 * pool_pop[cols]  # popularity as pure tiebreak
            keep = min(TOP_K + 1, len(cols))
            if keep == 0:
                updates.append((json.dumps([]), int(ids[i])))
                continue
            part = np.argpartition(-score, keep - 1)[:keep]
            order = part[np.argsort(-score[part])]
            out = [int(pool_ids[cols[j]]) for j in order if pool_ids[cols[j]] != ids[i]][:TOP_K]
            updates.append((json.dumps(out), int(ids[i])))
        done = min(start + CHUNK, X.shape[0])
        if (start // CHUNK) % 20 == 0 or done == X.shape[0]:
            print(f"[{name}]   {done:,}/{X.shape[0]:,}  ({time.time()-t0:.0f}s)")

    con.executemany(f"UPDATE movies SET {name}_recs = ? WHERE tmdb_id = ?", updates)
    con.commit()
    print(f"[{name}] done in {time.time() - t0:.0f}s")


def main():
    con = sqlite3.connect(DB)
    print("Loading catalog...")
    rows = con.execute(
        """SELECT tmdb_id, genres, keywords, "cast", director, overview, tagline,
                  popularity, vote_count FROM movies ORDER BY tmdb_id"""
    ).fetchall()
    ids = np.array([r[0] for r in rows], dtype=np.int64)
    pop_score = np.log1p(np.array([r[7] or 0.0 for r in rows]))
    pop_score = (pop_score / (pop_score.max() or 1.0)).astype(np.float32)
    pool_mask = np.array([(r[8] or 0) >= MIN_VOTES for r in rows])
    print(f"{len(rows):,} movies, {pool_mask.sum():,} in recommendation pool")

    dims = {
        "genre": ([f"{phrase_tokens(r[1], ',')} {phrase_tokens(r[2], '|')}" for r in rows],
                  True, {"min_df": 2, "token_pattern": r"[^ ]+"}),
        "cast": ([f"{phrase_tokens(r[3], ',')} {phrase_tokens(r[4], ',')}" for r in rows],
                 False, {"min_df": 2, "token_pattern": r"[^ ]+"}),
        # plain-word tokens for plot text; max_df drops non-discriminative words
        # to keep the similarity matrix sparse
        "desc": ([f"{r[5] or ''} {r[6] or ''}".lower() for r in rows],
                 False, {"min_df": 5, "max_df": 0.01, "stop_words": "english",
                         "token_pattern": r"(?u)\b\w\w+\b"}),
    }
    del rows

    for name, (texts, blend_pop, kwargs) in dims.items():
        build_dim(name, texts, pool_mask, pop_score, con, ids, blend_pop, kwargs)

    print("VACUUM...")
    con.execute("UPDATE movies SET keywords = NULL")  # build-only column, big
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"All dimensions complete. DB: {os.path.getsize(DB)/1e6:.0f} MB")


if __name__ == "__main__":
    main()
