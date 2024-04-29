import requests
from typing import Optional, Literal
from google.cloud import firestore
from datetime import datetime, timedelta, UTC
import time
from src.authenticate import SecretManager

SECRETS = SecretManager()

class Movie():
    """ Movie relevant requests."""
    
    def __init__(
            self, 
            id_: int, 
            token: str,
            db: firestore.Client,
            retention: int = SECRETS.m2w_movie_retention,
            details: Optional[dict] = None
            ) -> None:
        """ Bundles the movie related requests.
        
        Parameters
        ----------
            id_: the TMDB ID of the movie.
            token: the bearer token of the user.
            db: the firestore DB Client.
            retention: the cache retention period in seconds.
            details: the details of the movie from TMDB.
        """
        self.__id = id_
        self.__token = token
        self.db = db
        self.retention = retention
        if details is None:
            self.__init_details()
        else:
            self.__details = details

    def __init_details(self) -> None:
        """Populates the details attribute."""
        movie = self.db.collection('movies').document(str(self.id)).get()
        if movie.exists:
            movie_data = movie.to_dict()
            age = datetime.now(UTC) - movie_data['refreshed_at']
            if age.total_seconds() >= self.retention:
                refresh = True
            else:
                refresh = False
        else:
            refresh = True
        
        if refresh:
            self.__details = self.__wait(self.get_details)
            self.__details['official_trailer'] = self.__wait(self.get_trailer)
            self.__details['local_providers'] = self.__wait(self.get_watch_providers)
            self.__details['refreshed_at'] = datetime.now(UTC)
            self.db.collection('movies').document(str(self.id)).set(document_data=self.details)
        else:
            self.__details = self.db.collection('movies').document(str(self.id)).get().to_dict()

    def __wait(self, func, limit: int = SECRETS.tmdb_rate_limit):
        """Waits until limit ms passed if func finished faster."""
        start = datetime.now()
        result = func()
        duration = datetime.now() - start
        wait = limit - duration.microseconds
        if wait > 0:
            time.sleep(wait/1000)
        return result
    
    def __str__(self) -> str:
        return f'Movie({self.id}): {self.title}'
    
    def __repr__(self) -> str:
        return f"<class '{self.__class__.__name__}' id={self.id}, title={self.title}>"

    @property
    def id(self) -> int:
        return self.__id
    
    @property
    def details(self) -> dict:
        return self.__details
    
    @property
    def genres(self) -> str:
        genres = []
        for genre in self.__details["genres"]:
            genres.append(genre["name"])
        return ", ".join(genres)
    
    @property
    def title(self) -> str:
        if self.__details["original_language"] == "en":
            return self.__details["original_title"]
        else:
            return self.__details["title"]
        
    @property
    def overview(self) -> str:
        return self.__details["overview"]
    
    @property
    def poster_path(self) -> str:
        url = f'https://image.tmdb.org/t/p/original{self.__details["poster_path"]}'
        return url
    
    @property
    def release_date(self) -> str:
        return self.__details["release_date"]
    
    @property
    def status(self) -> bool:
        return self.__details["status"]
    
    @property
    def runtime(self) -> int:
        return self.__details["runtime"]

    @property
    def trailer(self) -> str:
        return self.__details['official_trailer']
    
    @property
    def watch_providers(self) -> list:
        return self.__details['local_providers']
    
    @property
    def tmdb_link(self) -> str:
        return f'{SECRETS.tmdb_home}movie/{self.id}'
    
    def get_providers_for_locale(
            self, 
            locale: str
            ) -> dict:
        """Return the watch providers for the given locale."""
        try:
            provider = self.watch_providers[locale].copy()
        except KeyError:
            provider = {
                'stream': [],
                'rent': [],
                'buy': []
            } 
        else:
            empty = []
            stream = provider.pop('flatrate', empty)
            rent = provider.pop('rent', empty)
            buy = provider.pop('buy', empty)
            provider = {
                'stream': stream,
                'rent': rent,
                'buy': buy
            }
            for cat, prov in provider.items():
                for elem in prov:
                    elem['logo_path'] = f"https://image.tmdb.org/t/p/original{elem['logo_path']}"
        return provider
    
    def get_datasheet_for_locale(self, locale: str) -> dict:
        """Return the movie datasheet for the given locale. """
        sheet = {
            "id": self.id,
            "title": self.title,
            "overview": self.overview,
            "genres": self.genres,
            "runtime": self.runtime,
            "trailer": self.trailer,
            "poster": self.poster_path,
            "release_date": self.release_date,
            "status": self.status,
            "providers": self.get_providers_for_locale(locale=locale),
            "tmdb": self.tmdb_link
        }
        return sheet
    
    def get_details(self) -> dict:
        """ Get details for the movie.

        Returns
        -------
            The details of the movie as a json.
        """
        url = f"https://api.themoviedb.org/3/movie/{self.id}?language=en-US"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }

        response = requests.get(url, headers=headers)
        response = response.json()
        details = {
            "genres":response["genres"],
            "homepage": response["homepage"],
            "id": response["id"],
            "imdb_id": response["imdb_id"],
            "original_language": response["original_language"],
            "original_title": response["original_title"],
            "overview": response["overview"],
            "poster_path": response["poster_path"],
            "release_date": response["release_date"],
            "runtime": response["runtime"],
            "status": response["status"],
            "tagline": response["tagline"],
            "title": response["title"],
        }
        return details
    
    def get_trailer(self) -> str:
        """ Get the trailer URL of the movie.
        
        Returns
        -------
            The URL of the official trailer of the movie.
        """
        url = f"https://api.themoviedb.org/3/movie/{self.id}/videos?language=en-US"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }

        response = requests.get(url, headers=headers)
        response = response.json()
        videos = response['results']

        if len(videos) > 0:
            trailer = {}
            for vid in videos:
                if vid['type'] == "Trailer":
                    if vid["official"]:
                        trailer = vid
                        break
                    elif trailer == {}:
                        trailer = vid
            if trailer == {}:
                trailer = videos[0]
            url = f"https://www.youtube.com/watch?v={trailer['key']}"
        else:
            url = "No trailer data."
        return url
    
    def get_watch_providers(self) -> Optional[dict]:
        """ Gets the watch providers of the movie.
        
        Returns
        -------
            The provider data of the movie.
        """
        url = f"https://api.themoviedb.org/3/movie/{self.__id}/watch/providers"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }    

        response = requests.get(url, headers=headers)
        response = response.json()
        providers = response['results']
        return providers




# get_details()
# {
#   "genres": [
#     {
#       "id": 18,
#       "name": "Drama"
#     },
#     {
#       "id": 53,
#       "name": "Thriller"
#     },
#     {
#       "id": 35,
#       "name": "Comedy"
#     }
#   ],
#   "homepage": "http://www.foxmovies.com/movies/fight-club",
#   "id": 550,
#   "imdb_id": "tt0137523",
#   "original_language": "en",
#   "original_title": "Fight Club",
#   "overview": "A ticking-time-bomb ...",
#   "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
#   "release_date": "1999-10-15",
#   "runtime": 139,
#   "status": "Released",
#   "tagline": "Mischief. Mayhem. Soap.",
#   "title": "Fight Club",
# }

# get_trailer
# {
#   "id": 550,
#   "results": [
#     {
#       "iso_639_1": "en",
#       "iso_3166_1": "US",
#       "name": "Fight Club (1999) Trailer - Starring Brad Pitt, Edward Norton, Helena Bonham Carter",
#       "key": "O-b2VfmmbyA",
#       "site": "YouTube",
#       "size": 720,
#       "type": "Trailer",
#       "official": false,
#       "published_at": "2016-03-05T02:03:14.000Z",
#       "id": "639d5326be6d88007f170f44"
#     },
#     {
#       "iso_639_1": "en",
#       "iso_3166_1": "US",
#       "name": "#TBT Trailer",
#       "key": "BdJKm16Co6M",
#       "site": "YouTube",
#       "size": 1080,
#       "type": "Trailer",
#       "official": true,
#       "published_at": "2014-10-02T19:20:22.000Z",
#       "id": "5c9294240e0a267cd516835f"
#     }
#   ]
# }
