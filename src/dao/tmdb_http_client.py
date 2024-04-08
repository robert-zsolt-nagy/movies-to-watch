import json
from typing import Any, Optional
import requests
from datetime import datetime
import time


class TmdbHttpClientException(Exception):
    """Base class for Exceptions of TmdbHttpClient"""
    def __init__(self, message: str):
        """Base class for Exceptions of TmdbHttpClient"""
        super().__init__(message)


def limit_request_rate(func, limit: float=1.000):
    """Wait for `limit` seconds or until `func()` returns, 
    whichever lasts longer.
    """
    def wrap_func(*args, **kwargs): 
        start = datetime.now()
        result = func(*args, **kwargs) 
        end = datetime.now()
        duration = end - start
        wait = limit * 1_000_000 - duration.microseconds
        if wait > 0:
            time.sleep(wait/1_000_000)
        return result 
    return wrap_func


def _process_response(response: requests.Response) -> Any:
    """Process the response and pass it on if everytihng is OK."""
    if response.status_code >= 200 & response.status_code < 300:
        try:
            return response.json()
        except json.decoder.JSONDecodeError as error:
            raise TmdbHttpClientException("Invalid Response: " + error.msg)
    elif response.status_code == 400:
        raise TmdbHttpClientException("Bad Request")
    elif response.status_code == 401:
        raise TmdbHttpClientException("Unauthorized")
    elif response.status_code == 404:
        raise TmdbHttpClientException("Not Found")
    elif response.status_code == 500:
        raise TmdbHttpClientException("Internal Server Error")
    else:
        raise TmdbHttpClientException(f"Response with status:{response.status_code}")


class TmdbHttpClient:
    """Handle the requests with the TMDB API"""
    def __init__(self, token: str, base_url: str = "https://api.themoviedb.org/3", session: Optional[requests.Session] = None):
        """Bundle all requests to the TMDB API
        
        Parameters
        ----------
        token: the bearer token for accessing the TMDB API.
        base_url: the base URL of the TMDB API.
        session: the session object used for connection pooling.
        """
        self.__base_url = base_url
        self.__token = token
        if session is None:
            self.__session = requests.Session()
        else:
            self.__session = session

    def get(self, path: str, params: Optional[dict] = None, additional_headers: Optional[dict] = None) -> Any:
        """Sends a GET request.
        
        Parameters
        ----------
        path: the specific API path
        params: the parameters of the request
        additional_headers: the additional headers of the request

        Returns:
        The response decoded as json.
        """
        default_headers = self.__get_default_headers()
        headers = self.__consolidate_headers(default_headers, additional_headers)
        url = self.__base_url + path
        response = self.__session.get(url=url, params=params, headers=headers)
        return _process_response(response)

    def post(
            self, 
            path: str, 
            content_type: str, 
            payload: dict, 
            additional_headers: Optional[dict] = None, 
            params: Optional[dict] = None
            ) -> Any:
        """Sends a POST request.
        
        Parameters
        ----------
        path: the specific API path
        content_type: the content type of the request.
        payload: the payload delivered by the request.
        additional_headers: the additional headers of the request.
        params: the parameters of the request

        Returns:
        The response decoded as json.
        """
        default_headers = self.__get_default_headers()
        headers = self.__consolidate_headers(default_headers, {"Content-Type":content_type}, additional_headers)
        url = self.__base_url + path
        response = self.__session.post(url=url, json=payload, headers=headers, params=params)
        return _process_response(response)

    def put(
            self, 
            path: str, 
            content_type: str, 
            payload: dict, 
            additional_headers: Optional[dict] = None
            ) -> Any:
        """Sends a PUT request.
        
        Parameters
        ----------
        path: the specific API path
        content_type: the content type of the request.
        payload: the payload delivered by the request.
        additional_headers: the additional headers of the request.

        Returns:
        The response decoded as json.
        """
        default_headers = self.__get_default_headers()
        headers = self.__consolidate_headers(default_headers, {"Content-Type":content_type}, additional_headers)
        url = self.__base_url + path
        response = self.__session.put(url=url, json=payload, headers=headers)
        return _process_response(response)

    def delete(self, path: str, params: Optional[dict] = None, additional_headers: Optional[dict] = None) -> Any:
        """Sends a DELETE request.
        
        Parameters
        ----------
        path: the specific API path
        params: the parameters of the request
        additional_headers: the additional headers of the request

        Returns:
        The response decoded as json.
        """
        default_headers = self.__get_default_headers()
        headers = self.__consolidate_headers(default_headers, additional_headers)
        url = self.__base_url + path
        response = self.__session.delete(url=url, params=params, headers=headers)
        return _process_response(response)

    def __get_default_headers(self) -> dict:
        """Returns a dictionary with the default headers."""
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }
    
    def __consolidate_headers(self, *args: Optional[dict]) -> dict:
        """Consolidate the received headers into a single header
        and return it.
        """
        headers = [arg for arg in args if arg is not None]
        result = {}
        for header in headers:
            result.update(**header)
        return result
