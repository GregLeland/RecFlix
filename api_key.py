# TMDB API key — read from the TMDB_API_KEY environment variable, or from a
# local .env file for development (gitignored). On Railway, set it under the
# service's Variables tab.
import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("TMDB_API_KEY")
if not api_key:
    raise RuntimeError(
        "TMDB_API_KEY is not set. Add it to your environment (Railway: Variables tab) "
        "or put TMDB_API_KEY=<key> in a .env file next to app.py."
    )
