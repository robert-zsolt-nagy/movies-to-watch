import json
from typing import Any, Optional
import requests

class TmdbHttpClientException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


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
    def __init__(self, token: str, base_url: str = "https://api.themoviedb.org/3"):
        """Bundle all requests to the TMDB API
        
        Parameters
        ----------
        token: the bearer token for accessing the TMDB API
        base_url: the base URL of the TMDB API
        """
        self.__base_url = base_url
        self.__token = token

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
        if additional_headers is None:
            headers = default_headers
        else:
            headers = {**default_headers, **additional_headers}

        url = self.__base_url + path
        response = requests.get(url=url, params=params, headers=headers)
        return _process_response(response)

    def post(self, path: str, content_type: str, payload: dict, additional_headers: Optional[dict] = None) -> Any:
        """Sends a POST request.
        
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
        default_headers["Content-Type"] = content_type
        if additional_headers is None:
            headers = default_headers
        else:
            headers = {**default_headers, **additional_headers}

        url = self.__base_url + path
        response = requests.post(url=url, json=payload, headers=headers)
        return _process_response(response)

    def put(self, path: str, content_type: str, payload: dict, additional_headers: Optional[dict] = None) -> Any:
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
        default_headers["Content-Type"] = content_type
        if additional_headers is None:
            headers = default_headers
        else:
            headers = {**default_headers, **additional_headers}

        url = self.__base_url + path
        response = requests.put(url=url, json=payload, headers=headers)
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
        if additional_headers is None:
            headers = default_headers
        else:
            headers = {**default_headers, **additional_headers}

        url = self.__base_url + path
        response = requests.delete(url=url, params=params, headers=headers)
        return _process_response(response)

    def __get_default_headers(self) -> dict:
        """Returns a dictionary with the default headers."""
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {self.__token}"
        }
