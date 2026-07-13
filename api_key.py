# TMDB API key — set the TMDB_API_KEY environment variable (Railway: add it
# under Variables). The fallback keeps local dev working, but rotate the old
# key at themoviedb.org/settings/api since it was committed to a public repo.
import os

api_key = os.environ.get("TMDB_API_KEY", "1ca3d9e71c549cbf25f486ad1ead8fd3")
