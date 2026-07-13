<center> <h1>"RecFlix" - A Movie Recommendation System</h1> </center>

Project URL: ~~http://gregrecflix.herokuapp.com~~ (Heroku's free tier was discontinued — see [Running it in 2026](#running-it-in-2026) below)

![Image of RecFlix](https://i.imgur.com/UgAF0em.jpg)

This project was based around a movie recommendation website idea. It uses a cosine similarity machine learning algorithm to suggest movies to users based on the genre, cast, and plot of their selection. Originally, the recommendations were based around the genre of the film, which returned fairly accurate results. After I got the website and its functionality fairly polished, I was unhappy with the limitation of providing recommendations in a specific genre. After thinking about how I could return more results, I decided to utilie the same cosine similarity algorithm and expand the results to other genres. I experimented with a few different methods, and decided to modify the MySQL database to include the cast and descriptions of the movies. From there, I processed the respective data and passed it into the ML algorithm. The results that were returned were very interesting, and I was actually able to find movies that I haven't seen, but actually seemed interesting.

Example of MySQL database creation:

```mysql
CREATE TABLE IF NOT EXISTS movies (
    `Column_1` INT,
    `movie_id` INT,
    `title` VARCHAR(82) CHARACTER SET utf8,
    `genres` VARCHAR(61) CHARACTER SET utf8,
    `imdbId` INT,
    `poster_path` VARCHAR(32) CHARACTER SET utf8,
    `tmdbId` INT,
    `movie_descriptions` VARCHAR(983) CHARACTER SET utf8,
    `cast` VARCHAR(134) CHARACTER SET utf8
);
INSERT INTO movies VALUES
    (0,1,'Toy Story (1995)','[''Animation'', "Children''s", ''Comedy'']',114709,'/rhIRbceoE9lR4veEXuwCC2wARtG.jpg',862,'Led by Woody, Andy''s toys live happily in his room until Andy''s birthday brings Buzz Lightyear onto the scene. Afraid of losing his place in Andy''s heart, Woody plots against Buzz. But when circumstances separate Buzz and Woody from their owner, the duo eventually learns to put aside their differences.','[''Tom Hanks'', ''Tim Allen'', ''Don Rickles'', ''Jim Varney'', ''Wallace Shawn'', ''John Ratzenberger'']'),
    (1,2,'Jumanji (1995)','[''Adventure'', "Children''s", ''Fantasy'']',113497,'/vzmL6fP7aPKNKPRTFnZmiUfciyV.jpg',8844,'When siblings Judy and Peter discover an enchanted board game that opens the door to a magical world, they unwittingly invite Alan -- an adult who''s been trapped inside the game for 26 years -- into their living room. Alan''s only hope for freedom is to finish the game, which proves risky as all three find themselves running from giant rhinoceroses, evil monkeys and other terrifying creatures.','[''Robin Williams'', ''Jonathan Hyde'', ''Kirsten Dunst'', ''Bradley Pierce'', ''Bonnie Hunt'', ''Bebe Neuwirth'']'),
```

To keep the package lighter and minimize the information required to host the site, the flask app makes multiple calls to different tmdb api endpoints to get the high-resolution box title images, movie poster images to display behind the movie information on the /rec/ page, movie runtime, and the trailer url (if available). The movie title, Tmdb ID, poster path, movie description, movie genres, top billed cast, and IMDB ID are stored in a MySQL database. 

Example of API call:
```python
url = []
tmdb = requests.get(f'https://api.themoviedb.org/3/movie/{j}?api_key={api_key}')
data = tmdb.json()
   if data.get("poster_path") != None:
      poster_path = data['poster_path']
      url.append("https://image.tmdb.org/t/p/original/" + poster_path)
```

To add additional useful functionality, I have implemented a search bar with an autocomplete feature to assist in movie selections. To expand on this, I have implemented 'fuzzy search' functionality to deliver close matches to search terms entered by the user and return them as suggestions on a search results page, while preventing crashes as a result of non-exact or misspelled titles. I discovered that the app would crash if someone searched for nothing or a ".", so I added a little bit of code to require a minimum of 2 characters before executing the search.

Example of search code:
```python
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
```

![Image of RecFlix](https://i.imgur.com/ZkByD99.jpg)

![Image of RecFlix Search](https://i.imgur.com/Ykah7qM.jpg)

The ‘RECFLIX’ project utilizes the following languages/libraries:
<ul>
  <li>Python</li>
  <li>Flask</li>
  <li>scikit-learn</li>
  <li>PyMySQL</li>
  <li>Pandas</li>
  <li>fuzzywuzzy</li>
  <li>WTForms</li>
  <li>Requests</li>
  <li>Javascript / AJAX</li>
  <li>HTML / CSS / Bootstrap</li>
</ul>

Recent Additions:

Major Updates:
<ul>
  <li>9-26-19 - Modified the database to include movie descriptions and top billed cast.</li>
  <li>9-26-19 - In addition to the genre suggestions, the /rec/ page now gives suggestions based on the similarity of the cast and plot of the film.</li>
  <li>9-26-19 - Added top billed cast to the movie information on /rec/ page.</li>
  <li>9-19-19 - Created a primitive search engine within the site that displays close matches to the user's search entry.</li>
</ul>

![Image of RecFlix Search Results](https://i.imgur.com/Wh7WT8L.jpg)

Minor Udpates / Bug Fixes:
<ul>
  <li>9-20-19 - Modified the autocomplete to accept fuzzy words and require a minimum of 2 characters to prevent crashes.</li>
  <li>9-27-19 - Updated the database and the code to fix crashes when searching for particular movies with special caracters in the title.</li>
  <li>9-27-19 - Fixed a bug whre a movie result was duplicated and causing the app to crash.</li>
</ul>

Future plans include:

<ul>
  <li>Modify the app to store user data and create user accounts where users will be able to rate a film. This information will then be clustered with the existing ratings data, and recommendations will be generated for each individual user. In this system, the ML algorithm will be able to learn and generate highly accurate suggestions based on user clustering.</li>
</ul>

## Running it in 2026

The 2026 revival removed the MySQL dependency entirely (the ClearDB add-on died with Heroku's free tier) — the app now loads `data/movies.csv` at startup. TMDB also re-generated their image paths and stopped putting trailers first in the videos endpoint; both are fixed, and stale image paths can always be refreshed by re-running the dataset build.

### Local setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows (use source .venv/bin/activate elsewhere)
pip install -r requirements.txt
echo TMDB_API_KEY=<your key> > .env   # gitignored; or set the env var directly
python scripts/build_dataset.py # only needed to refresh data/movies.csv
flask run
```

### Deploying to Railway

1. Push this repo to GitHub.
2. On [railway.app](https://railway.app): **New Project → Deploy from GitHub repo** → pick this repo. Railway auto-detects the `Procfile` and `requirements.txt`.
3. Under the service's **Variables** tab, add `TMDB_API_KEY` with your TMDB key.
4. Under **Settings → Networking**, click **Generate Domain** to get a public URL.

Every push to the default branch redeploys automatically. If posters ever break again (TMDB occasionally re-hashes image paths), run `python scripts/build_dataset.py` locally and push the updated `data/movies.csv`.
