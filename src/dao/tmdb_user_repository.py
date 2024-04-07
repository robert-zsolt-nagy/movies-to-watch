from typing import Optional
from src.dao.tmdb_http_client import TmdbHttpClient
from datetime import datetime, UTC

class TmdbUserRepositoryException(Exception):
    """Base class for Exceptions of TmdbUserRepository"""
    def __init__(self, message: str):
        """Base class for Exceptions of TmdbUserRepository"""
        super().__init__(message)

def is_expired(expires_at: str) -> bool:
    """Returns `True` if the current time is not before `expires_at` time."""
    try:
        exp = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
        validity = exp - datetime.now(UTC)
    except:
        return True
    else:
        if validity.seconds > 0:
            return False
        else:
            return True

class TmdbUserRepository():
    """Bundle of user related TMDB requests."""
    def __init__(self, tmdb_http_client: TmdbHttpClient) -> None:
        """Bundle of user related TMDB requests.
        
        Parameters
        ----------
        tmdb_http_client: the http client for TMDB API
        """
        self.__client = tmdb_http_client

    def create_request_token(self) -> dict:
        """ Request a new request token from TMDB.

        Returns
        -------
            The received request_token data as dict.
        """
        response = self.__client.get(path="/authentication/token/new")
        if response['success'] == True:
            return response
        else:
            raise TmdbUserRepositoryException("No new token received.")
        
    def get_user_permission_URL(
            self,
            request_token: str,
            expires_at: str,
            redirect_to: Optional[str] = None, 
            tmdb_url: str = "https://www.themoviedb.org",
            **kwargs # to adress the 'success' key in the response
            ) -> str:
        """ Ask the user for permission by an authentication URL.
        
        Parameters
        ----------
            request_token: the request token for the authentication request.
            expires_at: the expiration time of the request token in UTC timezone.
            redirect_to: the URL to redirect to after processing the authentication request.
            tmdb_url: the base URL of TMDB.

        Returns
        -------
            The relevant URL.
        """
        if is_expired(expires_at=expires_at):
            raise TmdbUserRepositoryException("Request token is expired.")
        elif redirect_to is None:
            url = f"{tmdb_url}/authenticate/{request_token}"
        else:
            url = f"{tmdb_url}/authenticate/{request_token}?redirect_to={redirect_to}"
        return url
    
    def create_session_id(
            self, 
            request_token: dict
            ) -> str:
        """ Create a session id for a particular request token.
        
        Parameters
        ----------
            request_token: the response received after requesting a new token.

        Returns
        -------
            The created session ID.
        """
        if is_expired(expires_at=request_token['expires_at']):
            raise TmdbUserRepositoryException("Request token is expired.")
        response = self.__client.post(
            path="/authentication/session/new",
            content_type="application/json",
            payload=request_token
        )
        if response['success'] == True:
            return response['session_id']
        else:
            raise TmdbUserRepositoryException("Requesting session_id was unsuccessful.")
        
    def get_account_data(self, session_id: Optional[str] = None) -> dict:
        """ Gets the account data of a TMDB user.
        
        Parameters
        ----------
            session_id: the current session ID.

        Returns
        -------
            The received response as a dictionary that contains the account's data.
        """
        response = self.__client.get(
            path=f'/account',
            params={'session_id': session_id}
        )
        return response
    
    def get_watchlist_movie(self, user_id: int, session_id: str, page: Optional[int]=None) -> tuple[list[dict], int]:
        """ Get data about the movies watchlist of the account.
        
        Parameters
        ----------
            user_id: the TMDB ID of the user.
            session_id: the session id of the user.
            page: the page of the watchlist that should be returned. 
            If omitted all pages will be returned in a single list.
        Returns
        -------
            A tuple containing the list of all the movies AND the number of pages.
        """
        if page is None:
            movies = []
            results, total_pages = self.get_watchlist_movie(
                user_id=user_id,
                session_id=session_id,
                page=1
            )
            if total_pages == 1:
                return (results, total_pages)
            else:
                movies += results
                for curr_page in range(2, total_pages+1):
                    results, _ = self.get_watchlist_movie(
                        user_id=user_id,
                        session_id=session_id,
                        page=curr_page
                    )
                    movies += results
                return (movies, total_pages)
        else:
            response = self.__client.get(
                path=f'/account/{user_id}/watchlist/movies',
                params={
                    'language': 'en-US',
                    'page': page,
                    'session_id': session_id,
                    'sort_by': 'created_at.desc'
                }
            )
            return (response["results"], response["total_pages"])
        
    def __edit_movie_watchlist(
            self,
            movie_id: int,
            add: bool,
            user_id: int,
            session_id: str
            ) -> dict:
        """Adds a movie to or removes a movie from the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        add: if True adds the movie, otherwise removes the movie
        user_id: the TMDB ID of the user.
        session_id: the session id of the user.

        Returns
        --------
        The response as a json.
        
        """
        movie_id = int(movie_id)
        response = self.__client.post(
            path=f'/account/{user_id}/watchlist',
            content_type="application/json",
            payload={
                'media_type': 'movie', 
                'media_id': movie_id, 
                'watchlist': add
            },
            params={'session_id': session_id}
        )
        return response
    
    def add_movie_to_watchlist(
            self,
            movie_id: int,
            user_id: int,
            session_id: str
            ) -> dict:
        """Adds a movie to the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        add: if True adds the movie, otherwise removes the movie
        user_id: the TMDB ID of the user.
        session_id: the session id of the user.

        Returns
        --------
        The response as a json.
        
        """
        response = self.__edit_movie_watchlist(
            movie_id=movie_id, 
            add=True,
            user_id=user_id,
            session_id=session_id
            )
        return response
    
    def remove_movie_from_watchlist(
            self,
            movie_id: int,
            user_id: int,
            session_id: str
            ) -> dict:
        """Remove a movie from the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        add: if True adds the movie, otherwise removes the movie
        user_id: the TMDB ID of the user.
        session_id: the session id of the user.

        Returns
        --------
        The response as a json.
        
        """
        response = self.__edit_movie_watchlist(
            movie_id=movie_id, 
            add=False,
            user_id=user_id,
            session_id=session_id
            )
        return response
