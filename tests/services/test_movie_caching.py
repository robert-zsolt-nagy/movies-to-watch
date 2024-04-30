from unittest import TestCase
from unittest.mock import MagicMock

from src.services.movie_caching import MovieCachingService, MovieNotFoundException, MovieCacheUpdateError, WatchlistCreationError
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.tmdb_user_repository import TmdbUserRepository
from src.dao.tmdb_movie_repository import TmdbMovieRepository
from src.dao.m2w_database import M2wMovieHandler, M2wUserHandler, M2WDatabase
from google.cloud import firestore
from datetime import datetime, UTC, timedelta

class TestMovieCachingService(TestCase):
    def test_get_movie_details_from_cache_should_return_dict(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        movie = MagicMock(firestore.DocumentReference)
        timestamp = datetime.now(UTC)
        movie.to_dict = MagicMock(return_value={
            'id': 1,
            'refreshed_at': timestamp
            })
        under_test.movie_handler.get_one = MagicMock(return_value=movie)
        
        #when
        repsonse = under_test.get_movie_details_from_cache(movie_id="1")

        #then
        self.assertEqual(repsonse, {
            'id': 1,
            'refreshed_at': timestamp
            })
        under_test.movie_handler.get_one.assert_called_with(id_='1')

    def test_get_movie_details_from_cache_should_raise_exception_if_expired(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w,
            m2w_movie_retention=5
        )
        movie = MagicMock(firestore.DocumentReference)
        timestamp = datetime.now(UTC) - timedelta(seconds=100)
        movie.to_dict = MagicMock(return_value={
            'id': 1,
            'refreshed_at': timestamp
            })
        under_test.movie_handler.get_one = MagicMock(return_value=movie)
        
        #when
        with self.assertRaises(MovieNotFoundException) as context:
            under_test.get_movie_details_from_cache(movie_id="1")

        #then
        self.assertIsInstance(context.exception, MovieNotFoundException)
        under_test.movie_handler.get_one.assert_called_with(id_='1')