from src.dao.m2w_graph_db_repository_movies import save_or_update_movie
from src.dao.tmdb_http_client import TmdbHttpClient
from src.services.movie_caching import MovieCachingService
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase, get_the_matrix_movie


class TestMovieCachingService(M2wDatabaseTestCase):

    def test_get_movie_details_from_cache_should_return_details(self):
        # given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            db=self.driver
        )
        tx = self.session.begin_transaction()
        movie = get_the_matrix_movie()
        save_or_update_movie(tx=tx, movie=movie)
        tx.commit()
        # when
        actual = under_test.get_movie_details_from_cache(movie_id=movie.movie_id)
        # then
        self.assertEqual(actual.movie_id, movie.movie_id)
        self.assertEqual(actual.title, movie.title)
        self.assertEqual(actual.overview, movie.overview)
        self.assertEqual(actual.poster_path, movie.poster_path)
        self.assertEqual(actual.release_date, movie.release_date)
        self.assertEqual(actual.official_trailer, movie.official_trailer)

    def test_get_movie_title_should_return_title(self):
        # given
        tmdb = TmdbHttpClient(token="ignore", base_url="url")
        under_test = MovieCachingService(
            tmdb_http_client=tmdb,
            db=self.driver
        )
        tx = self.session.begin_transaction()
        movie = get_the_matrix_movie()
        save_or_update_movie(tx=tx, movie=movie)
        tx.commit()
        # when
        actual = under_test.get_movie_title(movie_id=movie.movie_id)
        # then
        self.assertEqual(actual, movie.title)
