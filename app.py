from flask import Flask, jsonify, Response, render_template, request, redirect, url_for
import json
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField, TextAreaField, SubmitField, validators
from engine import *
from rapidfuzz import process
import requests
from api_key import api_key

app = Flask(__name__)
app.static_folder = 'static'

# CREATE A GENERIC SECRET KEY BECAUSE THE FORM REQUIRES IT FOR VALIDATION AND WE WON'T BE NEEDING ANYTHING SECURE FOR OUR PURPOSES
app.config.update(dict(
    SECRET_KEY="powerful secretkey",
    WTF_CSRF_SECRET_KEY="a csrf secret key"
))

# COMPILES A LIST OF MOVIE TITLES TO BE PASSED INTO THE AUTOCOMPLETE FORM
movie_list = movies['title'].tolist()

# INDEX ROUTE - SELECTS 6 MOVIES AT RANDOM FROM MOVIES DF AND DISPLAYS THEM ON THE PAGE AS A STARTING POINT
# ALSO LISTENS FOR THE POST FROM THE AUTOCOMPLETE FORM AND ROUTES THE FORM SUBMISSION TO THE REC ROUTE
@app.route("/", methods=['GET', 'POST'])
def index():
    form = SearchForm(request.form)
    if request.method == 'POST':
        form_cont = form.autocomp.data
        str2Match = form_cont
        strOptions = movie_list
        # GET THE STRING WITH THE HIGHEST MATCHING PERCENTAGE
        highest = process.extractOne(str2Match,strOptions)
        fuzzyresult = highest[0]
        movie_index = movies.loc[movies['title'] == fuzzyresult]
        movieID = str(movie_index['tmdbId'].iloc[0])
        # IF THE STRING IS AN EXACT MATCH, THERE IS NO NEED TO GO TO THE SEARCH PAGE. IF INPUT IS NOT GREATER THAN 1, DO NOTHING.
        if form_cont == fuzzyresult:
            return redirect('../rec/' + movieID)
        elif len(form_cont) > 1:
            return redirect('../results/' + form_cont)
        else:
            pass
    # CREATE A DATAFRAME WITH 6 RANDOM MOVIES FROM OUR DATABASE
    # POSTER PATHS COME STRAIGHT FROM THE DATASET (REFRESHED BY
    # scripts/build_dataset.py) SO THE HOMEPAGE NEEDS NO LIVE API CALLS
    rando_df = movies.sample(6)
    title2 = []
    url = []
    for x in range(6):
        title2.append(rando_df.tmdbId.iloc[x])
        url.append("https://image.tmdb.org/t/p/original" + rando_df.poster_path.iloc[x])
    return render_template('index.html', title2=title2, url=url, form=form)

@app.route("/results/<title>", methods=['GET', 'POST'])
def searchResults(title):
    form = SearchForm(request.form)
    if request.method == 'POST':
        form_cont = form.autocomp.data
        str2Match = form_cont
        strOptions = movie_list
        Ratios = process.extract(str2Match,strOptions)
        highest = process.extractOne(str2Match,strOptions)
        fuzzyresult = highest[0]
        movie_index = movies.loc[movies['title'] == fuzzyresult]
        movieID = str(movie_index['tmdbId'].iloc[0])
        # IF THE STRING IS AN EXACT MATCH, THERE IS NO NEED TO GO TO THE SEARCH PAGE. IF INPUT IS NOT GREATER THAN 1, DO NOTHING.
        if form_cont == fuzzyresult:
            return redirect('../rec/' + movieID)
        elif len(form_cont) > 1:
            return redirect('../results/' + form_cont)
        else:
            pass
    resultString = title
    resultOptions = movie_list
    Ratios = process.extract(resultString,resultOptions)
    resultList = []
    matchPer = []
    # EXTRACT THE MOVIE TITLES AND MATCH ACCURACY FROM OUR FUZZY SEARCH RESULTS
    for x in range(len(Ratios)):
        resultList.append(Ratios[x][0])
        matchPer.append(round(Ratios[x][1]))
    # CREATE A LIST OF LINKS FOR OUR RESULTS
    movieID = []
    movieURL = []
    resultPosters = []
    resultDescription = []
    for x in resultList:
        findFilm = movies.loc[movies['title'] == x]
        grabID = str(findFilm['tmdbId'].iloc[0])
        movieURL.append("../rec/" + grabID)
        # GET THE DESCRIPTIONS AND POSTERS FOR THE MOVIE RESULTS
        resultPosters.append("https://image.tmdb.org/t/p/original" + findFilm['poster_path'].iloc[0])
        tmdb_desc = requests.get(f'https://api.themoviedb.org/3/movie/{grabID}?api_key={api_key}')
        desc_data = tmdb_desc.json()
        # ALWAYS APPEND SO DESCRIPTIONS STAY LINED UP WITH THEIR POSTERS
        resultDescription.append(desc_data.get('overview') or '')
    return render_template('results.html', title=title, resultString=resultString, resultList=resultList, movieURL=movieURL, matchPer=matchPer, resultPosters=resultPosters, resultDescription=resultDescription, form=form)


@app.route("/rec/<title>", methods=['GET', 'POST'])
def movie_bot_final(title):
    form = SearchForm(request.form)
    # IDENTIFY THE TITLE THAT WAS PASSED IN
    titleloc = movies.loc[movies['tmdbId'] == int(title)]
    movieTitle = titleloc['title'].iloc[0]
    # GET THE DESCRIPTION OF THE MOVIE THAT WAS PASSED IN
    tmdb_desc = requests.get(f'https://api.themoviedb.org/3/movie/{title}?api_key={api_key}')
    desc_data = tmdb_desc.json()
    description = desc_data.get('overview') or ''
    # GET THE YOUTUBE TRAILER LINK FOR THE ID THAT WAS PASSED IN
    # TMDB NO LONGER PUTS THE TRAILER FIRST IN THE VIDEOS LIST (results[0] IS
    # OFTEN A CLIP OR FEATURETTE NOW), SO FILTER FOR AN ACTUAL YOUTUBE TRAILER
    tmdb_trailer = requests.get(f'https://api.themoviedb.org/3/movie/{title}/videos?api_key={api_key}')
    trailer_response = tmdb_trailer.json().get('results', [])
    yt_videos = [v for v in trailer_response if v.get('site') == 'YouTube' and v.get('key')]
    yt_trailers = [v for v in yt_videos if v.get('type') == 'Trailer'] or yt_videos
    if not yt_trailers:
        trailer_url = 'None'
    else:
        pick = next((v for v in yt_trailers if v.get('official')), yt_trailers[0])
        trailer_url = (f'https://www.youtube.com/watch?v={pick["key"]}')
    # FORM SUBMISSION
    if request.method == 'POST':
        form_cont = form.autocomp.data
        str2Match = form_cont
        strOptions = movie_list
        Ratios = process.extract(str2Match,strOptions)
        highest = process.extractOne(str2Match,strOptions)
        fuzzyresult = highest[0]
        movie_index = movies.loc[movies['title'] == fuzzyresult]
        movieID = str(movie_index['tmdbId'].iloc[0])
        # IF THE STRING IS AN EXACT MATCH, THERE IS NO NEED TO GO TO THE SEARCH PAGE. IF INPUT IS NOT GREATER THAN 1, DO NOTHING.
        if form_cont == fuzzyresult:
            return redirect('../rec/' + movieID)
        elif len(form_cont) > 1:
            return redirect('../results/' + form_cont)
        else:
            pass
    titles = movies['title']
    indices = pd.Series(movies.index, index=movies['title'])
    idx = indices[movieTitle]
    # -----------------------------
    # ML BASED ON THE MOVIE GENRE
    # -----------------------------
    # SIMILARITY IS COMPUTED PER-REQUEST FROM THE SPARSE TF-IDF MATRICES (SEE
    # engine.top_similar) INSTEAD OF PRECOMPUTED NxN COSINE MATRICES
    genre_movie_indices = top_similar(genre_matrix, idx)
    # RETURNS THE 12 MOST SIMILAR MOVIES BY GENRE
    genre_df = titles.iloc[genre_movie_indices].head(13).to_frame()
    # ----------------------------
    # ML BASED ON THE MOVIE CAST
    # ----------------------------
    cast_movie_indices = top_similar(cast_matrix, idx)
    # RETURNS THE 12 MOST SIMILAR MOVIES BY CAST
    cast_df = titles.iloc[cast_movie_indices].head(13).to_frame()
    # -----------------------------------
    # ML BASED ON THE MOVIE DESCRIPTION
    # -----------------------------------
    desc_movie_indices = top_similar(desc_matrix, idx)
    # RETURNS THE 12 MOST SIMILAR MOVIES BY DESCRIPTION
    desc_df = titles.iloc[desc_movie_indices].head(13).to_frame()
    # ------------------------------------------------------------------
    # REMOVING SEARCH TITLE FROM RESULTS AND RETURNING 12 RECS
    # ------------------------------------------------------------------
    genre_df = genre_df[genre_df.title != movieTitle]
    genre_df = genre_df.head(12)
    cast_df = cast_df[cast_df.title != movieTitle]
    cast_df = cast_df.head(12)
    desc_df = desc_df[desc_df.title != movieTitle]
    desc_df = desc_df.head(12)
    # ------------------------------------------------------------------
    # PROSESSING RESULTS AND CREATING ONE LARGE DATAFRAME
    # ------------------------------------------------------------------
    mv = pd.concat([genre_df,cast_df,desc_df]).reset_index(drop=True)
    cols = ['title']
    temp_df = mv.join(movies.set_index(cols), on=cols)
    # GETTING MOVIE INFORMATION
    moviename = []
    url1 = []
    movCastin = titleloc['cast'].iloc[0]
    movCastOut = movCastin.replace("'","").replace('"','').strip("][").split(', ')
    topCast = (movCastOut + ['', '', ''])[:3]
    # PULLS THE IMAGE URL FROM THE MOVIES DF AND APPENDS THEM TO THE URL PREFIX FOR THE MOVIE POSTERS
    # PASSES THE MOVIE POSTER URL INTO THE RECS.HTML PAGE
    titleurl = str("https://image.tmdb.org/t/p/original" + titleloc['poster_path'].iloc[0])
    backdropPath = desc_data.get('backdrop_path') or ''
    bgurl = ("https://image.tmdb.org/t/p/original" + backdropPath) if backdropPath else ''
    runtime = str(desc_data.get('runtime') or '')
    for film in temp_df.tmdbId:
        moviename.append(film)
    for poster in temp_df.poster_path:
        url1.append("https://image.tmdb.org/t/p/w185" + str(poster))
    return render_template('recs.html', moviename=moviename, url1=url1, topCast=topCast, movieTitle=movieTitle, titleurl=titleurl, bgurl=bgurl, form=form, description=description, runtime=runtime, trailer_url=trailer_url)

# SETS UP THE FORM WITH THE AUTOCOMP TEXT FIELD AND SUBMISSION BUTTON
class SearchForm(FlaskForm):
    autocomp = StringField('Enter Movie Title', id='movie_autocomplete')
    submit = SubmitField('Search')

# THE BRAINS OF THE AUTOCOMPLETE. PULLS THE MOVIES FROM THE LIST VARIABLE AND RETURNS A JSON THAT CAN BE PARSED BY THE JQUERY ON THE HTML PAGE
@app.route('/_autocomplete', methods=['GET'])
def autocomplete():
    return Response(json.dumps(movie_list), mimetype='application/json')

if __name__ == "__main__":
    app.run(debug=True)
