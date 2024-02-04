import tomllib
import requests
import webbrowser
from typing import Optional

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
        self.__BEARER_TOKEN = self.__SECRETS['tmdb']['bearer_token']
        self.__last_request_token = None
        self.__last_session = None

    @property
    def secrets(self):
        return self.__SECRETS

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
        url=f"https://www.themoviedb.org/authenticate/{token}"
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
        return response


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

    def get_watchlist_movie(self) -> list:
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



if __name__ == "__main__":
    authenticator = Authentication()

    # payload = authenticator.create_request_token()
    # print(authenticator.ask_user_permission())
    # permit = input("Permitted?")
    # if permit == "y":
    #     new_session = authenticator.create_session_id(payload=payload)
    #     print(f"session_id:{new_session}")
    
    SESSION_ID = authenticator.secrets['tmdb']['session_id']
    TOKEN = authenticator.secrets['tmdb']['bearer_token']
    account_data = authenticator.get_account_data(session_id=SESSION_ID)
    my_account = Account(token=TOKEN, session_id=SESSION_ID, **account_data)
    my_lists = my_account.get_lists()
    print("My lists:")
    for elem in my_lists:
        print(elem['name'])
    watchlist = my_account.get_watchlist_movie()
    print("Watchlist movies:")
    for movie in watchlist:
        print(movie['original_title'])