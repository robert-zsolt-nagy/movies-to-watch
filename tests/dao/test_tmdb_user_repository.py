from unittest import TestCase
from unittest.mock import MagicMock

from src.dao.tmdb_http_client import TmdbHttpClient, TmdbHttpClientException
from src.dao.tmdb_user_repository import TmdbUserRepository, TmdbUserRepositoryException
from datetime import datetime, timedelta, UTC

class TestTmdbUserRepository(TestCase):
    def test_create_request_token_should_raise_exception_if_unsuccessful(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "success": False,
            "expires_at": "2016-08-26 17:04:39 UTC",
            "request_token": "token"
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)
        
        # when
        with self.assertRaises(TmdbUserRepositoryException) as context:
            under_test.create_request_token()

        # then exception was raised
        self.assertIsInstance(context.exception, TmdbUserRepositoryException)
        client.get.assert_called_with(path="/authentication/token/new")

    def test_create_request_token_should_return_dicitonary(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "success": True,
            "expires_at": "2016-08-26 17:04:39 UTC",
            "request_token": "token"
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)
        
        # when
        response = under_test.create_request_token()

        # then exception was raised
        self.assertEqual(response, {
            "success": True,
            "expires_at": "2016-08-26 17:04:39 UTC",
            "request_token": "token"
        })
        client.get.assert_called_with(path="/authentication/token/new")

    def test_get_user_permission_URL_should_raise_error_if_expired(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        under_test = TmdbUserRepository(tmdb_http_client=client)

        # when 
        with self.assertRaises(TmdbUserRepositoryException) as context:
            under_test.get_user_permission_URL(
                request_token="token",
                expires_at="2016-08-26 17:04:39 UTC",
                tmdb_url="ignore"
            )

        # then
        self.assertIsInstance(context.exception, TmdbUserRepositoryException)

    def test_get_user_permission_URL_should_return_URL_if_valid(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        under_test = TmdbUserRepository(tmdb_http_client=client)
        expires_at = datetime.now(UTC) + timedelta(days=1)
        expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # when 
        response = under_test.get_user_permission_URL(
            request_token="token",
            expires_at=expires_at,
            tmdb_url="ignore"
        )

        # then
        self.assertEqual(response, "ignore/authenticate/token")

    def test_get_user_permission_URL_should_handle_redirect_and_success_arguments(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        under_test = TmdbUserRepository(tmdb_http_client=client)
        expires_at = datetime.now(UTC) + timedelta(days=1)
        expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        payload = {
            "success": True,
            "expires_at": expires_at,
            "request_token": "token"
        }

        # when 
        response = under_test.get_user_permission_URL(
            redirect_to="target",
            tmdb_url="ignore",
            **payload
        )

        # then
        self.assertEqual(response, "ignore/authenticate/token?redirect_to=target")

    def test_create_session_id_should_raise_error_if_token_expired(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.post = MagicMock(return_value={
            "success": True,
            "session_id": "session"
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)

        # when 
        with self.assertRaises(TmdbUserRepositoryException) as context:
            under_test.create_session_id(
                request_token={
                    "success": True,
                    "expires_at": "2016-08-26 17:04:39 UTC",
                    "request_token": "token"
                }
            )

        # then
        self.assertIsInstance(context.exception, TmdbUserRepositoryException)

    def test_create_session_id_should_raise_error_if_response_failed(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.post = MagicMock(return_value={
            "success": False,
            "session_id": "session"
        })
        expires_at = datetime.now(UTC) + timedelta(days=1)
        expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        under_test = TmdbUserRepository(tmdb_http_client=client)

        # when 
        with self.assertRaises(TmdbUserRepositoryException) as context:
            under_test.create_session_id(
                request_token={
                    "success": True,
                    "expires_at": expires_at,
                    "request_token": "token"
                }
            )

        # then
        self.assertIsInstance(context.exception, TmdbUserRepositoryException)

    def test_create_session_id_should_return_only_id(self):
        # given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.post = MagicMock(return_value={
            "success": True,
            "session_id": "session"
        })
        expires_at = datetime.now(UTC) + timedelta(days=1)
        expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        under_test = TmdbUserRepository(tmdb_http_client=client)

        # when 
        response = under_test.create_session_id(
            request_token={
                "success": True,
                "expires_at": expires_at,
                "request_token": "token"
            }
        )

        # then
        self.assertEqual(response, "session")
        client.post.assert_called_with(
            path="/authentication/session/new",
            content_type="application/json",
            payload={
                "success": True,
                "expires_at": expires_at,
                "request_token": "token"
            }
        )
    
    def test_get_account_data_should_return_values(self):
        #given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "avatar": {
                "gravatar": {
                "hash": "hash"
                },
                "tmdb": {
                "avatar_path": "/avatar.png"
                }
            },
            "id": 1,
            "iso_639_1": "en",
            "iso_3166_1": "CA",
            "name": "John Doe",
            "include_adult": False,
            "username": "johndoe"
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)

        #when
        response = under_test.get_account_data(session_id="session")

        #then
        self.assertEqual(response, {
            "avatar": {
                "gravatar": {
                "hash": "hash"
                },
                "tmdb": {
                "avatar_path": "/avatar.png"
                }
            },
            "id": 1,
            "iso_639_1": "en",
            "iso_3166_1": "CA",
            "name": "John Doe",
            "include_adult": False,
            "username": "johndoe"
        })
        client.get.assert_called_with(
            path='/account',
            params={'session_id': "session"}
        )

    def test_get_watchlist_movie_should_return_results_as_list(self):
        #given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        results = [
            {
            "adult": False,
            "backdrop_path": "/backdrop.jpg",
            "genre_ids": [
                878,
                18,
                53
            ],
            "id": 1,
            "original_language": "en",
            "original_title": "Title",
            "overview": "overview",
            "popularity": 37.148,
            "poster_path": "/poster.jpg",
            "release_date": "2012-02-01",
            "title": "Title",
            "video": False,
            "vote_average": 6.822,
            "vote_count": 4741
            },
            {
            "adult": False,
            "backdrop_path": "/backdrop.jpg",
            "genre_ids": [
                28,
                18,
                53
            ],
            "id": 2,
            "original_language": "en",
            "original_title": "Title",
            "overview": "overview",
            "popularity": 18.699,
            "poster_path": "/poster.jpg",
            "release_date": "2011-11-01",
            "title": "Title",
            "video": False,
            "vote_average": 5.676,
            "vote_count": 1190
            }
        ]
        page = {
            "page": 1,
            "results": results,
            "total_pages": 1,
            "total_results": 2
        }
        client.get = MagicMock(return_value=page)
        under_test = TmdbUserRepository(tmdb_http_client=client)

        #when
        response = under_test.get_watchlist_movie(user_id=1, session_id="session")

        #then
        self.assertEqual(response, results)
        client.get.assert_called_with(
            path=f'/account/1/watchlist/movies',
            params={
                'language': 'en-US',
                'page': 1,
                'session_id': "session",
                'sort_by': 'created_at.desc'
            }
        )

    def test_get_watchlist_movie_should_merge_multiple_pages(self):
        #given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        pages = [
            0,
            {
                "page": 1,
                "results": [
                    {
                        "id": 1,
                        "original_language": "en",
                        "original_title": "Title"
                    },
                    {
                        "id": 2,
                        "original_language": "en",
                        "original_title": "Title"
                    }
                ],
                "total_pages": 2,
                "total_results": 4
            },
            {
                "page": 2,
                "results": [
                    {
                        "id": 3,
                        "original_language": "en",
                        "original_title": "Title"
                    },
                    {
                        "id": 4,
                        "original_language": "en",
                        "original_title": "Title"
                    }
                ],
                "total_pages": 2,
                "total_results": 4
            }
        ]
        results = [
            {
                "id": 1,
                "original_language": "en",
                "original_title": "Title"
            },
            {
                "id": 2,
                "original_language": "en",
                "original_title": "Title"
            },
            {
                "id": 3,
                "original_language": "en",
                "original_title": "Title"
            },
            {
                "id": 4,
                "original_language": "en",
                "original_title": "Title"
            }
        ]
        def get_page(path, params):
            return pages[params['page']]

        client.get = MagicMock(side_effect=get_page)
        under_test = TmdbUserRepository(tmdb_http_client=client)

        #when
        response = under_test.get_watchlist_movie(user_id=1, session_id="session")

        #then
        self.assertEqual(response, results)
        client.get.assert_called_with(
            path=f'/account/1/watchlist/movies',
            params={
                'language': 'en-US',
                'page': 2,
                'session_id': "session",
                'sort_by': 'created_at.desc'
            }
        )

    def test_add_movie_to_watchlist_should_add_the_movie(self):
        #given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.post = MagicMock(return_value={
            "status_code": 1,
            "status_message": "Success."
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)

        #when
        response = under_test.add_movie_to_watchlist(
            movie_id=1,
            user_id=2,
            session_id="session"
        )

        #then
        self.assertEqual(response, {
            "status_code": 1,
            "status_message": "Success."
        })
        client.post.assert_called_with(
            path='/account/2/watchlist',
            content_type="application/json",
            payload={
                'media_type': 'movie', 
                'media_id': 1, 
                'watchlist': True
            },
            params={'session_id': "session"}
        )

    def test_remove_movie_from_watchlist_should_remove_the_movie(self):
        #given
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.post = MagicMock(return_value={
            "status_code": 1,
            "status_message": "Success."
        })
        under_test = TmdbUserRepository(tmdb_http_client=client)

        #when
        response = under_test.remove_movie_from_watchlist(
            movie_id=1,
            user_id=2,
            session_id="session"
        )

        #then
        self.assertEqual(response, {
            "status_code": 1,
            "status_message": "Success."
        })
        client.post.assert_called_with(
            path='/account/2/watchlist',
            content_type="application/json",
            payload={
                'media_type': 'movie', 
                'media_id': 1, 
                'watchlist': False
            },
            params={'session_id': "session"}
        )