# Import all the cool stuff that makes stuff look cool... oh, and the 'sciency' stuff...
import os

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# The 'stars' of the show - the movies themselves!
# Loaded from a local CSV (built by scripts/build_dataset.py) instead of the
# old ClearDB MySQL instance, which was decommissioned along with Heroku's
# free tier.
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "movies.csv")
movies = pd.read_csv(DATA_PATH)

# Break up the big genre string into a string array
movies['genres'] = movies['genres'].str.split('|')
# Convert genres to string value
movies['genres'] = movies['genres'].fillna("").astype('str')
movies['cast'] = movies['cast'].fillna("").astype('str')
movies['movie_descriptions'] = movies['movie_descriptions'].fillna("").astype('str')

# CONVERTS THE MOVIE GENRES INTO A MATRIX OF TF-IDF FEATURES
tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), min_df=1, stop_words='english')

# The TF-IDF matrices are kept sparse and similarity is computed one row at a
# time on request. Precomputing the full NxN cosine matrices (the old
# approach) needs ~350MB of RAM for 3,800 movies, which blows past the 512MB
# tier of most hosts; a single row is milliseconds and a few KB.
genre_matrix = tf.fit_transform(movies['genres'])
cast_matrix = tf.fit_transform(movies['cast'])
desc_matrix = tf.fit_transform(movies['movie_descriptions'])


def top_similar(matrix, idx, n=20):
    """Indices of the n movies most similar to row idx, best first (idx excluded)."""
    sims = linear_kernel(matrix[idx], matrix).ravel()
    order = sims.argsort()[::-1]
    return [i for i in order if i != idx][:n]
