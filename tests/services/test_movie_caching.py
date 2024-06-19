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
        response = under_test.get_movie_details_from_cache(movie_id="1")

        #then
        self.assertEqual(response, {
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

    def test_get_movie_details_from_tmdb_should_return_dict(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        timestamp = datetime.now(UTC)
        under_test.movie_repo.get_details_by_id = MagicMock(return_value={
            'id': 1,
            'refreshed_at': timestamp
            })
        under_test.movie_repo.get_trailer = MagicMock(return_value="trailerURL")
        under_test.movie_repo.get_watch_providers = MagicMock(return_value={"AA":{"flatrate":"provider"}})
        
        #when
        response = under_test.get_movie_details_from_tmdb(movie_id=1)

        #then
        self.assertEqual(response['id'], 1)
        self.assertEqual(response['official_trailer'], "trailerURL")
        self.assertEqual(response['local_providers'], {"AA":{"flatrate":"provider"}})
        self.assertGreaterEqual(response['refreshed_at'], timestamp)
        under_test.movie_repo.get_details_by_id.assert_called_with(movie_id=1)
        under_test.movie_repo.get_trailer.assert_called_with(movie_id=1)
        under_test.movie_repo.get_watch_providers.assert_called_with(movie_id=1)

    def test_get_movie_details_should_return_cached_if_cached(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.get_movie_details_from_cache = MagicMock(return_value="cached_movie")
        under_test.get_movie_details_from_tmdb = MagicMock(return_value="tmdb_movie")
        
        #when
        response = under_test.get_movie_details(movie_id=1)

        #then
        self.assertEqual(response, "cached_movie")
        under_test.get_movie_details_from_cache.assert_called_with(movie_id="1")

    def test_get_movie_details_should_return_tmdb_if_cache_expired(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        def raise_error(*args, **kwargs):
            raise MovieNotFoundException
        under_test.get_movie_details_from_cache = MagicMock(side_effect=raise_error)
        under_test.get_movie_details_from_tmdb = MagicMock(return_value="tmdb_movie")
        
        #when
        response = under_test.get_movie_details(movie_id=1)

        #then
        self.assertEqual(response, "tmdb_movie")
        under_test.get_movie_details_from_cache.assert_called_with(movie_id="1")

    def test_update_movie_cache_with_details_by_id_should_pass_on_params(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.movie_handler.set_data = MagicMock(return_value=True)
        
        #when
        response = under_test.update_movie_cache_with_details_by_id(movie_id="1", details={"my":"details"})

        #then
        self.assertEqual(response, True)
        under_test.movie_handler.set_data.assert_called_with(id_="1", data={"my":"details"})

    def test_check_and_update_movie_cache_by_id_should_not_call_tmdb_if_cached(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.get_movie_details_from_cache = MagicMock(return_value={'refreshed_at':datetime.now(UTC)})
        under_test.get_movie_details_from_tmdb = MagicMock(return_value="tmdb_movie")
        
        #when
        response = under_test.check_and_update_movie_cache_by_id(movie_id=1)

        #then
        self.assertEqual(response, True)
        under_test.get_movie_details_from_cache.assert_called_with(movie_id="1")
        under_test.get_movie_details_from_tmdb.assert_not_called()

    def test_check_and_update_movie_cache_by_id_should_not_call_cache_if_forced(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.get_movie_details_from_cache = MagicMock(return_value="cached_movie")
        under_test.get_movie_details_from_tmdb = MagicMock(return_value="tmdb_movie")
        under_test.update_movie_cache_with_details_by_id = MagicMock(return_value=True)
        
        #when
        response = under_test.check_and_update_movie_cache_by_id(movie_id=1, forced=True)

        #then
        self.assertEqual(response, True)
        under_test.get_movie_details_from_tmdb.assert_called_with(movie_id=1)
        under_test.update_movie_cache_with_details_by_id.assert_called_with(movie_id='1', details="tmdb_movie")
        under_test.get_movie_details_from_cache.assert_not_called()

    def test_check_and_update_movie_cache_by_id_should_call_tmdb_if_not_cached(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        def raise_error(*args, **kwargs):
            raise MovieNotFoundException
        under_test.get_movie_details_from_cache = MagicMock(side_effect=raise_error)
        under_test.get_movie_details_from_tmdb = MagicMock(return_value="tmdb_movie")
        under_test.update_movie_cache_with_details_by_id = MagicMock(return_value=True)
        
        #when
        response = under_test.check_and_update_movie_cache_by_id(movie_id=1, forced=True)

        #then
        self.assertEqual(response, True)
        under_test.get_movie_details_from_tmdb.assert_called_with(movie_id=1)
        under_test.update_movie_cache_with_details_by_id.assert_called_with(movie_id='1', details="tmdb_movie")
        under_test.get_movie_details_from_cache.assert_not_called()

    def test_get_combined_watchlist_of_users_should_eliminate_duplicates(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        user_1 = MagicMock(firestore.DocumentSnapshot)
        user_1.to_dict = MagicMock(return_value={
            'tmdb_session':'session1',
            'tmdb_user':{
                'id':1
            }
            })
        user_2 = MagicMock(firestore.DocumentSnapshot)
        user_2.to_dict = MagicMock(return_value={
            'tmdb_session':'session2',
            'tmdb_user':{
                'id':2
            }
            })
        gen_users = (u for u in [user_1, user_2])
        def get_watchlist(user_id, session_id):
            watch_data = {
                1:[{"id":1},{"id":2},{"id":3}],
                2:[{"id":2},{"id":3},{"id":4}]
            }
            return watch_data[user_id]
        under_test.user_repo.get_watchlist_movie = MagicMock(side_effect=get_watchlist)

        #when
        response = under_test.get_combined_watchlist_of_users(users=gen_users)

        #then
        self.assertEqual(response, [{"id":1},{"id":2},{"id":3},{"id":4}])
        under_test.user_repo.get_watchlist_movie.assert_called_with(user_id=2, session_id="session2")

    def test_movie_cache_update_job_should_pass_on_all_paramaters(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.user_handler.get_all = MagicMock(return_value="all_users")
        under_test.get_combined_watchlist_of_users = MagicMock(return_value=[{'id':1}])
        under_test.check_and_update_movie_cache_by_id = MagicMock(return_value="success")

        #when 
        response = under_test.movie_cache_update_job()

        #then
        self.assertEqual(response, True)
        under_test.user_handler.get_all.assert_called_once()
        under_test.get_combined_watchlist_of_users.assert_called_with(users="all_users")
        under_test.check_and_update_movie_cache_by_id.assert_called_with(movie_id="1")

    def test_add_movie_to_blocklist_should_pass_correct_parameter(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.movie_handler.add_to_blocklist = MagicMock(return_value=True)

        #when
        response = under_test.add_movie_to_blocklist(movie_id="1", blocklist="blocklist")
        
        #then
        self.assertEqual(response, True)
        under_test.movie_handler.add_to_blocklist.assert_called_with(movie_id="1", blocklist="blocklist")

    def test_remove_movie_from_blocklist_should_pass_correct_parameter(self):
        #given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        m2w = MagicMock(M2WDatabase)
        m2w.movie = MagicMock(M2wMovieHandler)
        m2w.user = MagicMock(M2wUserHandler)
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            m2w_database=m2w
        )
        under_test.movie_handler.remove_from_blocklist = MagicMock(return_value=True)

        #when
        response = under_test.remove_movie_from_blocklist(movie_id="1", blocklist="blocklist")
        
        #then
        self.assertEqual(response, True)
        under_test.movie_handler.remove_from_blocklist.assert_called_with(movie_id="1", blocklist="blocklist")
    
