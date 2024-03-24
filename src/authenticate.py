import tomllib
import requests
import webbrowser
from typing import Optional
from random import randint
import json

def generate_id(length: int = 8) -> str:
    """Generate a random alphanumeric id with a given length.
    
    Parameters
    ----------
    length: the length of the id
    """
    seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    id = []
    for _ in range(length):
        ix = randint(0, len(seed)-1)
        id.append(seed[ix])
    return ''.join(id)    

class SecretManager():
    """ Reads and manages the external secrets."""

    def __init__(self, secret_storage: str='secrets.toml') -> None:
        """ Open the secret storage and read the secrets."""
        with open(secret_storage, mode="rb") as vault:
            self.__SECRETS = tomllib.load(vault)

    @property
    def secrets(self) -> str:
        """ All of the secrets."""
        return self.__SECRETS
    
    @property
    def tmdb_rate_limit(self) -> str:
        """ The rate limit for tmdb requests."""
        return self.__SECRETS['tmdb']['rate_limit']
    
    @property
    def tmdb_token(self) -> str:
        """ The bearer token for authentication"""
        return self.__SECRETS['tmdb']['auth']['bearer_token']
    
    @property
    def tmdb_session(self) -> str:
        """ The session ID for authentication"""
        return self.__SECRETS['tmdb']['auth']['session_id']
    
    @property
    def tmdb_API(self) -> str:
        """ The base URL for the tmdb API."""
        return self.__SECRETS['tmdb']['URLs']['API_base_URL']
    
    @property
    def tmdb_home(self) -> str:
        """ The home URL for the tmdb."""
        return self.__SECRETS['tmdb']['URLs']['home_URL']
    
    @property
    def tmdb_image(self) -> str:
        """ The base URL for the tmdb image storage."""
        return self.__SECRETS['tmdb']['URLs']['image_URL']
    
    @property
    def firebase_cert(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firebase']['certificate']
    
    @property
    def firebase_config(self) -> str:
        """ The path to the firebase configuration."""
        return self.__SECRETS['firebase']['config']
    
    @property
    def firestore_cert(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firestore']['certificate']
    
    @property
    def firestore_project(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firestore']['project']
    
    @property
    def m2w_base_URL(self) -> str:
        """ The base movies-to-watch URL."""
        return self.__SECRETS['m2w']['base_URL']
    
    @property
    def m2w_movie_retention(self) -> str:
        """ The base movies-to-watch URL."""
        return self.__SECRETS['m2w']['movie_retention']
        

class Authentication():
    """ Handles the authentication with TMDB"""

    def __init__(self, secrets: Optional[dict] = None) -> None:
        """ Contains the secrets for user Authentication. 
        
        Parameters
        ----------
            secrets: the dictionary containing the secrets necessary for authentication. 
        If omitted uses the content of the secrets.toml file.

        Secrets format
        --------------
        ```
        {
            'tmdb':{
                'bearer_token':your_API_Read_Access_Token
            }
        }
        ```
        """
        if secrets is None:
            with open('secrets.toml', mode="rb") as vault:
                self.__SECRETS = tomllib.load(vault)
        else:
            self.__SECRETS = secrets
        self.__BEARER_TOKEN = self.__SECRETS['tmdb']['auth']['bearer_token']
        self.__last_request_token = None
        try:
            self.__last_session = self.__SECRETS['tmdb']['auth']['session_id']
        except KeyError:
            self.__last_session = None    
        self.__account_data = None
        self.__approve_id = None

    @classmethod
    def from_dict(secrets: dict):
        """ Creates an Authentication object from the secrets dictionary.
        
        Parameters
        ----------
            secrets: the dictionary containing the secrets necessary for authentication. 

        Secrets format
        --------------
        ```
        {
            'tmdb':{
                'bearer_token':your_API_Read_Access_Token
            }
        }
        ```
        """
        return Authentication(secrets=secrets)    

    @property
    def secrets(self):
        return self.__SECRETS
    
    @property
    def session(self):
        return self.__last_session
    
    @property
    def approve_id(self):
        return self.__approve_id
    
    @property
    def request_token(self):
        return self.__last_request_token

    def create_request_token(self, token: Optional[str] = None) -> dict:
        """ Request a new request token.
        
        Parameters
        ----------
            token: your API Read Access Token. If omitted it uses the cached default.

        Returns
        -------
            The received response as a dictionary.
        """
        url = "https://api.themoviedb.org/3/authentication/token/new"

        if token is None:
            token = self.__BEARER_TOKEN
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(url, headers=headers)
        # {'success': true, 'expires_at': '', 'request_token': ''}
        response = response.json()
        
        if response['success'] == True:
            self.__last_request_token = response['request_token']
        else:
            self.__last_request_token = None
            raise Exception("Request unsuccessful.")
        return response
    
    def ask_user_permission(
            self,
            token: Optional[str] = None, 
            _open: bool = False
            ) -> str:
        """ Ask the user for permission by an authentication URL.
        
        Parameters
        ----------
            token: the request token. If omitted the last cached token is used.
            _open: if true, opens the relevant URL in a new tab.

        Returns
        -------
            The relevant URL.
        """
        if token is None:
            token = self.__last_request_token
        self.__approve_id = generate_id()
        url=f"https://www.themoviedb.org/authenticate/{token}?redirect_to={self.secrets['m2w']['base_URL']}/approved/{self.__approve_id}"
        if _open:
            webbrowser.open_new_tab(url=url)
        return url

    def create_session_id(
            self, 
            payload: dict,
            token: Optional[str] = None,
            ) -> str:
        """ Create a session id.
        
        Parameters
        ----------
            payload: the response received after requesting a new token.
            token: your API Read Access Token. If omitted it uses the cached default.

        Returns
        -------
            The created session ID.
        """
        url = "https://api.themoviedb.org/3/authentication/session/new"

        if token is None:
            token = self.__BEARER_TOKEN
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        response = requests.post(url, json=payload, headers=headers)
        # {"success":true,"session_id":""}
        response = response.json()
        if response['success'] == True:
            self.__last_session = response['session_id']
            return response['session_id']
        else:
            raise Exception("Request unsuccessful.")

    def get_account_data(self, session_id: Optional[str] = None) -> dict:
        """ Gets the account data of a user.
        
        Parameters
        ----------
            session_id: the current session ID. If omitted the cached value is used.

        Returns
        -------
            The received response as a dictionary that contains the account's data.
        """
        if session_id is None:
            session_id = self.__last_session
        url = f'https://api.themoviedb.org/3/account?session_id={session_id}'

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__BEARER_TOKEN}"
        }

        response = requests.get(url, headers=headers)
        # {
        #     "avatar":{
        #         "gravatar":{"hash":""},
        #         "tmdb":{"avatar_path":null}
        #     },
        #     "id":12345678,
        #     "iso_639_1":"en",
        #     "iso_3166_1":"HU",
        #     "name":"",
        #     "include_adult":false,
        #     "username":""
        # }
        response = response.json()
        self.__account_data = response
        return response
    
    def create_account(self):
        """ Returns a new Account object instance 
        based on the Authentication details."""
        new_account = Account(
            token=self.__BEARER_TOKEN, 
            session_id=self.__last_session,
            **self.__account_data
            )
        return new_account
    

class Account():
    """ Account relevant requests."""

    __token = None
    __session_id = None
    avatar = None
    id = None
    iso_639_1 = None
    iso_3166_1 = None
    name = None
    include_adult = False
    username = None
    blocklist = []
    watchlist_movie = []
    m2w_id = None
    m2w_nick = None
    m2w_email = None

    def __init__(
            self, 
            id: int,
            token: str,
            session_id: str,
            avatar: Optional[dict] = None,
            iso_639_1: Optional[str] = None,
            iso_3166_1: Optional[str] = None,
            name: Optional[str] = None,
            include_adult: bool = False,
            username: Optional[str] = None,
            blocklist: list = [],
            m2w_id: Optional[str] = None,
            m2w_nick: Optional[str] = None,
            m2w_email: Optional[str] = None
            ) -> None:
        """ Bundles the account related requests. 
        
        Parameters
        ----------
            id: the ID of the TMBD account.
            token: the API read access token.
            session_id: the ID of the session.
            **kwargs: the attributes of the account if known.
        """
        self.id = id
        self.__token = token
        self.__session_id = session_id
        self.avatar = avatar
        self.iso_639_1 = iso_639_1
        self.iso_3166_1 = iso_3166_1
        self.name = name
        self.include_adult = include_adult
        self.username = username
        self.blocklist = blocklist
        self.m2w_id = m2w_id
        self.m2w_nick = m2w_nick
        self.m2w_email = m2w_email

    def get_lists(self) -> list:
        """ Gets data about the lists of the account.
        
        Returns
        -------
            A list that contains the data for every list of the account.
        """
        url = f"https://api.themoviedb.org/3/account/{self.id}/lists?page=1&session_id={self.__session_id}"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }

        response = requests.get(url, headers=headers)
        response = response.json()
        results = response['results']
        return results
        # {"page":1,
        #  "results":[
        #      {"description":"my_description",
        #       "favorite_count":0,
        #       "id":1234567,
        #       "item_count":1,
        #       "iso_639_1":"en",
        #       "list_type":"movie",
        #       "name":"my_list",
        #       "poster_path":null},
        #       ],
        # "total_pages":1,
        # "total_results":2}

    def get_watchlist_movie(self) -> list[dict]:
        """ Get data about the movies watchlist of the account.
        
        Returns
        -------
            A list containing all movies on the accounts watchlist.
        """
        url = f"https://api.themoviedb.org/3/account/{self.id}/watchlist/movies?language=en-US&page=1&session_id={self.__session_id}&sort_by=created_at.desc"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }

        response = requests.get(url, headers=headers)
        response = response.json()
        results = response["results"]
        return results
        # {'adult': False, 
        # 'backdrop_path': '/kjQBrc00fB2RjHZB3PGR4w9ibpz.jpg', 
        # 'genre_ids': [28, 12, 878], 
        # 'id': 123456, 
        # 'original_language': 'en', 
        # 'original_title': 'The Creator', 
        # 'overview': 'Amid a future war...', 
        # 'popularity': 243.422, 
        # 'poster_path': '/vBZ0qvaRxqEhZwl6LWmruJqWE8Z.jpg', 
        # 'release_date': '2023-09-27', 
        # 'title': 'The Creator', 
        # 'video': False, 
        # 'vote_average': 7.138, 
        # 'vote_count': 2120}
    
    def __str__(self) -> str:
        return f"<TMDB Account ID:{self.id} Name:{self.username}>"
    
    def __edit_movie_watchlist(
            self,
            movie_id: int,
            add: bool
            ) -> dict:
        """Adds a movie to or removes a movie from the movie watchlist.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        add: if True adds the movie, otherwise removes the movie

        Returns
        --------
        The response as a json.
        
        """
        movie_id = int(movie_id)
        url = f"https://api.themoviedb.org/3/account/{self.id}/watchlist?session_id={self.__session_id}"

        payload = {
            'media_type': 'movie', 
            'media_id': movie_id, 
            'watchlist': add
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    
    def add_movie_to_watchlist(
            self,
            movie_id: int,
            ) -> dict:
        """Adds a movie to the movie watchlist.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB

        Returns
        --------
        The response as a json.
        
        """
        response = self.__edit_movie_watchlist(movie_id=movie_id, add=True)
        return response
    
    def remove_movie_from_watchlist(
            self,
            movie_id: int,
            ) -> dict:
        """Remove a movie from the movie watchlist.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB

        Returns
        --------
        The response as a json.
        
        """
        response = self.__edit_movie_watchlist(movie_id=movie_id, add=False)
        return response