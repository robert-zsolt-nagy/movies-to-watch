from typing import Optional
from src.dao.tmdb_http_client import TmdbHttpClient

class TmdbUserRepositoryException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class tmdbUserRepository():
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
            The received `request_token` and `expires_at` data as dict.
        """
        response = self.__client.get(path="/authentication/token/new")
        if response['success'] == True:
            token = {
                "expires_at": response["expires_at"],
                "request_token": response["request_token"]
            }
            return token
        else:
            raise TmdbUserRepositoryException("No new token received.")