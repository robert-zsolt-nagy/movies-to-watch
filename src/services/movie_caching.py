from collections.abc import Generator
from datetime import datetime, UTC
from typing import Union, Optional

from expiringdict import ExpiringDict
from google.cloud import firestore

from src.dao.m2w_database import M2WDatabase
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.tmdb_movie_repository import TmdbMovieRepository
from src.dao.tmdb_user_repository import TmdbUserRepository


class MovieNotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class MovieCacheUpdateError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class WatchlistCreationError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MovieCachingService():
    """Handles the movie caching and data retreival."""
    def __init__(
            self, 
            tmdb_http_client: TmdbHttpClient, 
            m2w_database: M2WDatabase,
            m2w_movie_retention: int = 3600,
            cache: Optional[ExpiringDict] = None
            ) -> None:
        """Handles the movie caching and data retreival. 
        
        Parameters
        ----------
        tmdb_http_client: the client that handles the requests with the TMDB API.
        m2w_database: bundles the firestore related methods of M2W.
        m2w_movie_retention: the retention period of cached movies in seconds.
        cache: the in memory cache object.

        """
        self.user_repo = TmdbUserRepository(tmdb_http_client=tmdb_http_client)
        self.movie_repo = TmdbMovieRepository(tmdb_http_client=tmdb_http_client)
        self.movie_handler = m2w_database.movie
        self.user_handler = m2w_database.user
        self.movie_retention = m2w_movie_retention
        if cache is None:
            self.in_memory_cache = ExpiringDict(max_len=200, max_age_seconds=m2w_movie_retention)
        else:
            self.in_memory_cache = cache

    def get_movie_details_from_cache(self, movie_id: str) -> dict:
        """Get the cached movie details from the M2W Database.
        
        Parameters
        ----------
        movie_id: the TMDB ID of the movie as a string.

        Returns
        -------
        The result as a dictionary.

        Raises
        ------
        MovieNotFoundException if the movie does not exist or 
        cache is expired.
        """
        try:
            details = self.in_memory_cache.get(movie_id)
            if details is None:
                movie = self.movie_handler.get_one(id_=movie_id)
                details = movie.to_dict()
                age = datetime.now(UTC) - details['refreshed_at']
                if age.total_seconds() > self.movie_retention:
                    raise MovieNotFoundException("Movie not cached.")
                self.in_memory_cache[movie_id] = details
        except Exception:
            raise MovieNotFoundException("Movie not cached.")
        else:
            return details
        
    def get_movie_details_from_tmdb(self, movie_id: int) -> dict:
        """Get the movie details from the TMDB Database.
        
        Parameters
        ----------
        movie_id: the TMDB ID of the movie as an integer.

        Returns
        -------
        The result as a dictionary.

        Raises
        ------
        MovieNotFoundException if the movie does not exist.
        """
        try:
            details = self.movie_repo.get_details_by_id(movie_id=movie_id)
            details['official_trailer'] = self.movie_repo.get_trailer(movie_id=movie_id)
            details['local_providers'] = self.movie_repo.get_watch_providers(movie_id=movie_id)
            details['refreshed_at'] = datetime.now(UTC)
        except Exception as e:
            raise MovieNotFoundException(f"Movie {movie_id} not found on TMDB. Error:{e}")
        else:
            return details
        
    def get_movie_details(self, movie_id: Union[str, int]) -> dict:
        """Get the movie details from M2W if cached or from TMDB if not cached.
        
        Parameters
        ----------
        movie_id: the TMDB ID of the movie as an integer or string.

        Returns
        -------
        The result as a dictionary.

        Raises
        ------
        MovieNotFoundException if the movie does not exist.
        """
        try:
            m2w_details = self.get_movie_details_from_cache(movie_id=str(movie_id))
        except MovieNotFoundException:
            tmdb_details = self.get_movie_details_from_tmdb(movie_id=int(movie_id))
            return tmdb_details
        else:
            return m2w_details
        
    def update_movie_cache_with_details_by_id(self, movie_id: str, details: dict) -> bool:
        """Update the cached movie with details.

        Parameters
        ----------
        movie_id: the TMDB ID of the movie as a string.
        details: the movie details from TMDB.

        Returns
        -------
        True if successful.

        Raises
        ------
        MovieCacheUpdateError if the update failed.
        
        """
        try:
            from_cache = self.in_memory_cache.get(movie_id)
            if from_cache == details:
                return True
            self.movie_handler.set_data(
                id_=str(movie_id),
                data=details
            )
            self.in_memory_cache[str(movie_id)] = details
        except Exception:
            raise MovieCacheUpdateError("Error during update.")
        else:
            return True
        
    def check_and_update_movie_cache_by_id(self, movie_id: Union[str, int], forced: bool=False) -> bool:
        """Check the cached content for movie and update if missing or expired.
        
        Parameters
        ----------
        movie_id: the TMDB ID of the movie as a string or integer.
        forced: if True update the cache regardless of current cache content.

        Returns
        -------
        True if successful.

        Raises
        ------
        MovieCacheUpdateError if the update failed.
        
        """
        if forced:
            try:
                tmdb_details = self.get_movie_details_from_tmdb(movie_id=int(movie_id))
                self.update_movie_cache_with_details_by_id(movie_id=str(movie_id), details=tmdb_details)
            except MovieNotFoundException:
                raise MovieCacheUpdateError("Movie not found in TMDB")
            else:
                return True
            
        try:
            _ = self.get_movie_details_from_cache(movie_id=str(movie_id))
        except MovieNotFoundException:
            try:
                tmdb_details = self.get_movie_details_from_tmdb(movie_id=int(movie_id))
                self.update_movie_cache_with_details_by_id(movie_id=str(movie_id), details=tmdb_details)
            except MovieNotFoundException:
                raise MovieCacheUpdateError("Movie not found in TMDB")
            else:
                return True
        else:
            return True
        
    def get_combined_watchlist_of_users(self, users: Generator) -> list:
        """Get the watchlist of all users and consolidate them in a single list.
        
        Parameters
        ----------
        users: a generator of all relevant users.

        Returns
        -------
        The consolidated data as a single list.

        Raises
        ------
        WatchlistCreationError if any error occures.

        """
        try:
            watchlist_data = []
            for user in users:
                user_data = user.to_dict()
                watchlist = self.user_repo.get_watchlist_movie(
                    user_id=user_data['tmdb_user']['id'],
                    session_id=user_data['tmdb_session']
                )
                watchlist_data.append(watchlist)
            consolidated = self._consolidate_watchlists(watchlist_data)
        except Exception:
            raise WatchlistCreationError("Watchlist creation failed.")
        else:
            return consolidated

    @staticmethod
    def _consolidate_watchlists(watchlists: list) -> list:
        """Consolidates the received watchlists into a single list.
        
        Parameters
        ----------
        watchlists: the list of the unconsolidated watchlists.

        Returns
        -------
        The consolidated watchlist without duplicates.
        """
        result = {}
        for watchlist in watchlists:
            for movie in watchlist:
                result[movie['id']] = movie
        return [movie for movie in result.values()]
    
    def movie_cache_update_job(self) -> bool:
        """Caches the details of every movie from every users watchlist.
        
        Returns
        -------
        True if successful.
        
        Raises
        ------
        MovieCacheUpdateError in case of any error.
        """
        try:
            all_users = self.user_handler.get_all()
            watchlist_union = self.get_combined_watchlist_of_users(users=all_users)
            for movie in watchlist_union:
                self.check_and_update_movie_cache_by_id(
                    movie_id=str(movie['id'])
                )
        except Exception:
            raise MovieCacheUpdateError("Error during update job.")
        else:
            return True
        
    def add_movie_to_blocklist(self, movie_id: str, blocklist: firestore.CollectionReference) -> bool:
        """Adds a movie to the blocklist of the member.
        
        Parameters
        ----------
        movie_id: ID of the movie in M2W.
        blocklist: the reference of the affected blocklist.

        Returns
        -------
        True if successfull, False otherwise.
        """
        return self.movie_handler.add_to_blocklist(movie_id=movie_id, blocklist=blocklist)

    def remove_movie_from_blocklist(self, movie_id: str, blocklist: firestore.CollectionReference) -> bool:
        """Removes the movie from the blocklist.
        
        Parameters
        ----------
        movie_id: ID of the movie in TMDB.
        blocklist: the reference of the affected blocklist.

        Returns
        -------
        True if successfull, False otherwise.
        """
        return self.movie_handler.remove_from_blocklist(movie_id=movie_id, blocklist=blocklist)