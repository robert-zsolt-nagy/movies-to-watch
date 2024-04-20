from unittest import TestCase
from unittest.mock import MagicMock

from src.dao.tmdb_http_client import TmdbHttpClient, TmdbHttpClientException
from src.dao.tmdb_movie_repository import TmdbMovieRepository, NoTrailerDataException


class TestTmdbMovieRepository(TestCase):
    def test_get_details_by_id_should_filter_response_fields_when_movie_is_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "genres": [{1: "comedy"}, {2: "action"}],
            "homepage": "http://example.com",
            "id": 1,
            "imdb_id": 123,
            "original_language": "en-US",
            "original_title": "Example movie",
            "overview": "Overview text",
            "poster_path": "/poster/path.jpg",
            "release_date": "2001-01-01",
            "runtime": 210,
            "status": "status",
            "tagline": "tagline",
            "title": "Example movie",
            "video": False,
            "vote_average": 3,
            "vote_count": 1
        })
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_details_by_id(movie_id)

        # then
        self.assertEqual(result, {
            "genres": [{1: "comedy"}, {2: "action"}],
            "homepage": "http://example.com",
            "id": 1,
            "imdb_id": 123,
            "original_language": "en-US",
            "original_title": "Example movie",
            "overview": "Overview text",
            "poster_path": "/poster/path.jpg",
            "release_date": "2001-01-01",
            "runtime": 210,
            "status": "status",
            "tagline": "tagline",
            "title": "Example movie"
        })
        client.get.assert_called_with(path=f"/movie/1", params={"language": "en-US"})

    def test_get_details_by_id_should_raise_error_when_movie_content_is_not_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(side_effect=TmdbHttpClientException("Movie is not found."))
        under_test = TmdbMovieRepository(client)

        # when
        self.assertRaises(TmdbHttpClientException, lambda: under_test.get_details_by_id(movie_id))

        # then exception was raised
        client.get.assert_called_with(path=f"/movie/1", params={"language": "en-US"})

    def test_get_trailer_should_return_the_trailer_url_when_only_one_official_trailer_is_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "results": [{
                "key": "123",
                "type": "Trailer",
                "official": True
            }]
        })
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_trailer(movie_id)

        # then
        self.assertEqual(result, "https://www.youtube.com/watch?v=123")
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_trailer_should_return_the_trailer_url_when_only_unofficial_trailer_is_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "results": [{
                "key": "345",
                "type": "Trailer",
                "official": False
            }]
        })
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_trailer(movie_id)

        # then
        self.assertEqual(result, "https://www.youtube.com/watch?v=345")
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_trailer_should_return_the_official_trailer_url_when_multiple_trailers_are_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "results": [
                {
                    "key": "678",
                    "type": "Trailer",
                    "official": False
                },
                {
                    "key": "123",
                    "type": "Trailer",
                    "official": True
                },
                {
                    "key": "345",
                    "type": "Trailer",
                    "official": False
                }
            ]
        })
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_trailer(movie_id)

        # then
        self.assertEqual(result, "https://www.youtube.com/watch?v=123")
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_trailer_should_return_the_first_trailer_url_when_multiple_videos_are_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "results": [
                {
                    "key": "678",
                    "type": "Video",
                    "official": False
                },
                {
                    "key": "123",
                    "type": "Trailer",
                    "official": False
                },
                {
                    "key": "345",
                    "type": "Video",
                    "official": False
                }
            ]
        })
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_trailer(movie_id)

        # then
        self.assertEqual(result, "https://www.youtube.com/watch?v=123")
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_trailer_should_raise_error_when_movie_is_not_found(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(side_effect=TmdbHttpClientException("Movie is not found."))
        under_test = TmdbMovieRepository(client)

        # when
        self.assertRaises(TmdbHttpClientException, lambda: under_test.get_trailer(movie_id))

        # then exception was raised
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_trailer_should_raise_error_when_video_list_is_empty(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(return_value={
            "results": [
            ]
        })
        under_test = TmdbMovieRepository(client)

        # when
        self.assertRaises(NoTrailerDataException, lambda: under_test.get_trailer(movie_id))

        # then exception was raised
        client.get.assert_called_with(path=f"/movie/1/videos", params={"language": "en-US"})

    def test_get_watch_providers_should_only_return_results(self):
        # given
        movie_id = 1
        client = TmdbHttpClient(token="ignore", base_url="ignore")
        client.get = MagicMock(
            return_value={
                "id": 1,
                "results": {
                    "HU": {
                    "link": "https://www.themoviedb.org/movie/1-test-movie/watch?locale=HU",
                    "flatrate": [
                        {
                        "logo_path": "/emthp39XA2YScoYL1p0sdbAH2WA.jpg",
                        "provider_id": 119,
                        "provider_name": "Amazon Prime Video",
                        "display_priority": 12
                        }
                    ],
                    "rent": [
                        {
                        "logo_path": "/peURlLlr8jggOwK53fJ5wdQl05y.jpg",
                        "provider_id": 2,
                        "provider_name": "Apple TV",
                        "display_priority": 1
                        },
                        {
                        "logo_path": "/tbEdFQDwx5LEVr8WpSeXQSIirVq.jpg",
                        "provider_id": 3,
                        "provider_name": "Google Play Movies",
                        "display_priority": 3
                        }
                    ],
                    "buy": [
                        {
                        "logo_path": "/peURlLlr8jggOwK53fJ5wdQl05y.jpg",
                        "provider_id": 2,
                        "provider_name": "Apple TV",
                        "display_priority": 1
                        },
                        {
                        "logo_path": "/tbEdFQDwx5LEVr8WpSeXQSIirVq.jpg",
                        "provider_id": 3,
                        "provider_name": "Google Play Movies",
                        "display_priority": 3
                        }
                    ]
                    }
                }    
            }
        )
        under_test = TmdbMovieRepository(client)

        # when
        result = under_test.get_watch_providers(movie_id=movie_id)

        # then
        self.assertEqual(result, {
                    "HU": {
                    "link": "https://www.themoviedb.org/movie/1-test-movie/watch?locale=HU",
                    "flatrate": [
                        {
                        "logo_path": "/emthp39XA2YScoYL1p0sdbAH2WA.jpg",
                        "provider_id": 119,
                        "provider_name": "Amazon Prime Video",
                        "display_priority": 12
                        }
                    ],
                    "rent": [
                        {
                        "logo_path": "/peURlLlr8jggOwK53fJ5wdQl05y.jpg",
                        "provider_id": 2,
                        "provider_name": "Apple TV",
                        "display_priority": 1
                        },
                        {
                        "logo_path": "/tbEdFQDwx5LEVr8WpSeXQSIirVq.jpg",
                        "provider_id": 3,
                        "provider_name": "Google Play Movies",
                        "display_priority": 3
                        }
                    ],
                    "buy": [
                        {
                        "logo_path": "/peURlLlr8jggOwK53fJ5wdQl05y.jpg",
                        "provider_id": 2,
                        "provider_name": "Apple TV",
                        "display_priority": 1
                        },
                        {
                        "logo_path": "/tbEdFQDwx5LEVr8WpSeXQSIirVq.jpg",
                        "provider_id": 3,
                        "provider_name": "Google Play Movies",
                        "display_priority": 3
                        }
                    ]
                    }
                })
        client.get.assert_called_with(path=f"/movie/1/watch/providers")