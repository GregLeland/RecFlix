from flask import Flask, jsonify, Response, render_template, request, redirect, url_for
import json
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
import requests

import engine
from api_key import api_key

app = Flask(__name__)
app.static_folder = 'static'

# CREATE A GENERIC SECRET KEY BECAUSE THE FORM REQUIRES IT FOR VALIDATION AND WE WON'T BE NEEDING ANYTHING SECURE FOR OUR PURPOSES
app.config.update(dict(
    SECRET_KEY="powerful secretkey",
    WTF_CSRF_SECRET_KEY="a csrf secret key"
))

IMG_ORIGINAL = "https://image.tmdb.org/t/p/original"
IMG_THUMB = "https://image.tmdb.org/t/p/w185"


# SETS UP THE FORM WITH THE AUTOCOMP TEXT FIELD AND SUBMISSION BUTTON
class SearchForm(FlaskForm):
    autocomp = StringField('Enter Movie Title', id='movie_autocomplete')
    submit = SubmitField('Search')


def handle_search_post(form):
    """Shared by all three pages: exact title -> its rec page, otherwise the
    fuzzy results page."""
    text = (form.autocomp.data or "").strip()
    movie_id = engine.resolve_title(text)
    if movie_id:
        return redirect(url_for('movie_bot_final', tmdb_id=movie_id))
    if len(text) > 1:
        return redirect(url_for('searchResults', title=text))
    return None


# INDEX ROUTE - SHOWS 6 RANDOM WELL-KNOWN MOVIES AS A STARTING POINT
@app.route("/", methods=['GET', 'POST'])
def index():
    form = SearchForm(request.form)
    if request.method == 'POST':
        response = handle_search_post(form)
        if response:
            return response
    picks = engine.random_movies(6)
    title2 = [row['tmdb_id'] for row in picks]
    url = [IMG_ORIGINAL + row['poster_path'] for row in picks]
    return render_template('index.html', title2=title2, url=url, form=form)


@app.route("/results/<title>", methods=['GET', 'POST'])
def searchResults(title):
    form = SearchForm(request.form)
    if request.method == 'POST':
        response = handle_search_post(form)
        if response:
            return response
    matches = engine.search(title, 5)
    # the template shows 4 result boxes; make sure there are always enough
    while len(matches) < 4:
        filler = engine.random_movies(1)[0]
        matches.append((filler['tmdb_id'], engine.get_movie(filler['tmdb_id'])['display_title'], 0))
    resultList, matchPer, movieURL, resultPosters, resultDescription = [], [], [], [], []
    for movie_id, display_title, score in matches:
        movie = engine.get_movie(movie_id)
        resultList.append(display_title)
        matchPer.append(score)
        movieURL.append(url_for('movie_bot_final', tmdb_id=movie_id))
        resultPosters.append(IMG_ORIGINAL + movie['poster_path'])
        resultDescription.append(movie['overview'] or '')
    return render_template('results.html', title=title, resultString=title,
                           resultList=resultList, movieURL=movieURL, matchPer=matchPer,
                           resultPosters=resultPosters, resultDescription=resultDescription,
                           form=form)


@app.route("/rec/<int:tmdb_id>", methods=['GET', 'POST'])
def movie_bot_final(tmdb_id):
    form = SearchForm(request.form)
    if request.method == 'POST':
        response = handle_search_post(form)
        if response:
            return response
    movie = engine.get_movie(tmdb_id)
    if movie is None:
        return redirect(url_for('index'))

    movieTitle = movie['display_title']
    description = movie['overview'] or ''
    runtime = str(movie['runtime'] or '')
    topCast = [c.strip() for c in (movie['cast'] or '').split(',')[:3]]
    topCast += [''] * (3 - len(topCast))
    titleurl = IMG_ORIGINAL + movie['poster_path']

    # LIVE TMDB CALLS FOR WHAT THE CATALOG DOESN'T STORE: the backdrop image
    # and the trailer. TMDB no longer orders trailers first in /videos, so
    # filter for an actual YouTube trailer.
    bgurl = ''
    trailer_url = 'None'
    try:
        details = requests.get(
            f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}',
            timeout=10).json()
        if details.get('backdrop_path'):
            bgurl = IMG_ORIGINAL + details['backdrop_path']
        videos = requests.get(
            f'https://api.themoviedb.org/3/movie/{tmdb_id}/videos?api_key={api_key}',
            timeout=10).json().get('results', [])
        yt = [v for v in videos if v.get('site') == 'YouTube' and v.get('key')]
        trailers = [v for v in yt if v.get('type') == 'Trailer'] or yt
        if trailers:
            pick = next((v for v in trailers if v.get('official')), trailers[0])
            trailer_url = f'https://www.youtube.com/watch?v={pick["key"]}'
    except requests.RequestException:
        pass  # page still renders from the catalog if TMDB is unreachable

    # PRECOMPUTED RECOMMENDATIONS: genre row, cast row, plot row (12 each)
    rec_rows = engine.recommendations(tmdb_id)
    moviename, url1 = [], []
    for row in rec_rows:
        while len(row) < 12:  # last-resort filler so the template grid is full
            extra = engine.random_movies(1)[0]
            row.append((extra['tmdb_id'], extra['poster_path']))
        for rec_id, poster in row[:12]:
            moviename.append(rec_id)
            url1.append(IMG_THUMB + (poster or ''))

    return render_template('recs.html', moviename=moviename, url1=url1,
                           topCast=topCast, movieTitle=movieTitle, titleurl=titleurl,
                           bgurl=bgurl, form=form, description=description,
                           runtime=runtime, trailer_url=trailer_url)


# SERVER-SIDE AUTOCOMPLETE: jQuery UI calls this with ?term= on each
# keystroke; results are ranked by popularity so obscure titles only surface
# on near-exact input. (The old version shipped every title to the browser —
# fine at 3,800 movies, not at 923,000.)
@app.route('/_autocomplete', methods=['GET'])
def autocomplete():
    return jsonify(engine.autocomplete(request.args.get('term', ''), 20))


if __name__ == "__main__":
    app.run(debug=True)
