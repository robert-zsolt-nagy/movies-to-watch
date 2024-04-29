from typing import Optional
from src.dao.movie_repository import MovieRepository
from src.dao.tmdb_http_client import TmdbHttpClient

class NoTrailerDataException(Exception):
    """Exception that occures if a trailer is not found by TmdbMovieRepository"""
    def __init__(self, message: str):
        """Exception that occures if a trailer is not found by TmdbMovieRepository"""
        super().__init__(message)


class TmdbMovieRepository(MovieRepository):
    """Movie relevant requests."""
    def __init__(self, tmdb_http_client: TmdbHttpClient) -> None:
        """Bundle of movie related TMDB requests.
        
        Parameters
        ----------
        tmdb_http_client: the http client for TMDB API
        """
        self.__client = tmdb_http_client

    def get_details_by_id(self, movie_id: int) -> dict:
        """Return the details of a movie with `movie_id`.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        """
        response = self.__client.get(
            path=f"/movie/{movie_id}", params={"language": "en-US"})
        return {
            "genres": response["genres"],
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

    def get_trailer(self, movie_id: int) -> str:
        """Get the URL for the best trailer of the movie.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        """
        response = self.__client.get(
            path=f"/movie/{movie_id}/videos", params={"language": "en-US"}
            )
        videos = response['results']
        return _find_best_trailer(videos)

    def get_watch_providers(self, movie_id: int) -> Optional[dict]:
        """Gets the watch providers for the movie.
        
        Parameters
        ----------
        movie_id: the ID of the movie in TMDB
        """
        response = self.__client.get(
            path=f"/movie/{movie_id}/watch/providers")
        return response['results']


def _find_best_trailer(videos: list[dict]) -> str:
    """Return the URL of the best video from the videos.
    
    Parameters
    ----------
    videos: a list of dictionaries each containing the video data for a video.

    Returns
    -------
    The URL of the best trailer or "No trailer data." if no video data received.
    """
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
        return url
    else:
        raise NoTrailerDataException("No trailer data found.")
