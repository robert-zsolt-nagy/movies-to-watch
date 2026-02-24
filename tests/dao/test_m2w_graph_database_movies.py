from datetime import datetime, timedelta, date

from flask import session

from src.dao.m2w_graph_db_entities import VoteValue, Movie, Genre
from src.dao.m2w_graph_db_repository_movies import save_or_update_movie, keep_movie_ids_where_update_is_needed, \
    delete_details_of_obsolete_movies, get_all_genres_by_ids, get_all_movies_for_watchlist
from src.dao.m2w_graph_db_repository_votes_and_watch_status import vote_for_movie, mark_movie_as_watched, \
    get_all_watch_history_of_watchlist
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase, get_the_matrix_movie


class TestM2wGraphDatabaseMovies(M2wDatabaseTestCase):

    def test_save_or_update_movie_should_save_movie_details_when_creating_movie(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()
        # when
        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=to_save.movie_id, vote_value=VoteValue.YEAH)
        tx.commit()
        # then
        actual = self.find_single_movie(movie_id=to_save.movie_id)
        self.assert_movie_equals(actual, to_save)

    def test_save_or_update_movie_should_remove_missing_genres_when_updating_movie_details(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()
        to_save.genres = [
            Genre(1, "A"),
            Genre(2, "B"),
            Genre(3, "Action"),
            Genre(4, "Science Fiction")
        ]

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=to_save.movie_id, vote_value=VoteValue.YEAH)
        tx.commit()
        to_save.genres = [
            Genre(3, "Action"),
            Genre(4, "Science Fiction")
        ]
        # when
        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        genres = get_all_genres_by_ids(tx=tx, genre_ids=[3, 5, 6])
        tx.commit()
        # then
        actual = self.find_single_movie(movie_id=to_save.movie_id)
        self.assert_movie_equals(actual, to_save)
        self.assertEqual(len(genres), 1)
        self.assert_genre_equals(genres[0], to_save.genres[0])

    def test_save_or_update_movie_should_remove_all_genres_when_updating_movie_details_with_empty_genre_list(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=to_save.movie_id, vote_value=VoteValue.YEAH)
        tx.commit()
        to_save.genres = []
        # when
        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        movies_for_watchlist = get_all_movies_for_watchlist(tx=tx, watchlist_id=self.watchlist_id)
        tx.commit()
        # then
        actual = self.find_single_movie(movie_id=to_save.movie_id)
        self.assert_movie_equals(actual, to_save)
        self.assertEqual(len(movies_for_watchlist), 1)
        self.assert_movie_equals(movies_for_watchlist[0], to_save)

    def test_keep_movie_ids_where_update_is_needed_should_find_old_movies_when_they_were_not_updated_recently(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()
        to_save.updated_at = datetime.now() - timedelta(days=31)

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = keep_movie_ids_where_update_is_needed(tx=tx, movie_ids=[to_save.movie_id])
        tx.commit()
        # then
        self.assertListEqual(actual, [to_save.movie_id])

    def test_keep_movie_ids_where_update_is_needed_should_find_recent_movies_when_they_were_not_updated_today(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()
        to_save.release_date = date.today() - timedelta(days=1)
        to_save.updated_at = datetime.now() - timedelta(days=2)

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = keep_movie_ids_where_update_is_needed(tx=tx, movie_ids=[to_save.movie_id])
        tx.commit()
        # then
        self.assertListEqual(actual, [to_save.movie_id])

    def test_keep_movie_ids_where_update_is_needed_should_not_return_id_when_a_movie_is_up_to_date(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = keep_movie_ids_where_update_is_needed(tx=tx, movie_ids=[to_save.movie_id])
        tx.commit()
        # then
        self.assertListEqual(actual, [])

    def test_keep_movie_ids_where_update_is_needed_should_return_id_when_a_movie_is_missing_or_is_only_a_stub(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        tx.commit()
        expected = [self.movie_id, self.movie_id + 1, self.movie_id + 2]
        # when
        tx = self.session.begin_transaction()
        actual = keep_movie_ids_where_update_is_needed(tx=tx, movie_ids=expected)
        tx.commit()
        # then
        self.assertListEqual(actual, expected)

    def test_delete_details_of_obsolete_movies_should_delete_a_movie_when_it_was_never_watched_and_has_no_votes(self):
        # given
        self.insert_default_user_and_movie()
        self.session.run(
            query="""
                MATCH (m:Movie) 
                WHERE m.id = $movie_id
                SET m.updated_at = $updated_at
            """,
            parameters={
                "movie_id": self.movie_id,
                "updated_at": datetime.now() - timedelta(days=31)
            }
        )
        to_save = get_the_matrix_movie()
        to_save.updated_at = datetime.now() - timedelta(days=31)

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=to_save)
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=to_save.movie_id, vote_value=VoteValue.NAH)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        delete_details_of_obsolete_movies(tx=tx)
        tx.commit()
        # then
        found_id_records = self.session.run(query="""
                MATCH (m:Movie) 
                RETURN m.id as id
            """).fetch(10)
        existing_ids = []
        for record in found_id_records:
            existing_ids.append(record["id"])
        self.assertListEqual(existing_ids, [to_save.movie_id])

    def test_delete_details_of_obsolete_movies_should_remove_details_of_a_movie_when_it_was_watched_but_has_no_votes(
            self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_the_matrix_movie()
        to_save.updated_at = datetime.now() - timedelta(days=31)

        tx = self.session.begin_transaction()
        save_or_update_movie(tx=tx, movie=Movie(
            movie_id=self.movie_id,
            title="Title",
            overview=None,
            duration=None,
            poster_path=None,
            genres=[],
            official_trailer=None,
            original_language=None,
            release_date=None,
            status="RELEASED",
            updated_at=datetime.now() - timedelta(days=31)
        ))
        save_or_update_movie(tx=tx, movie=to_save)
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=self.movie_id, vote_value=VoteValue.NAH)
        mark_movie_as_watched(tx=tx, user_id=self.user_id, movie_id=to_save.movie_id)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        watched = get_all_watch_history_of_watchlist(tx=tx, user_ids=[self.user_id], movie_ids=[to_save.movie_id])
        delete_details_of_obsolete_movies(tx=tx)
        tx.commit()
        # then
        found_id_records = self.session.run(query="""
                MATCH (m:Movie) 
                RETURN m.id as id, keys(m) as property_names
            """).fetch(10)
        existing_ids = {}
        for record in found_id_records:
            existing_ids[record["id"]] = set(record["property_names"])
        self.assert_id_to_list_dict_equals(existing_ids, {
            self.movie_id: {"id", "status", "title", "updated_at"},
            to_save.movie_id: {"id"}
        })
        self.assertEqual(len(watched), 1)
        self.assertEqual(watched[0].user_id, self.user_id)
        self.assertEqual(watched[0].movie_id, to_save.movie_id)

    def assert_id_to_list_dict_equals(self, actual: dict[int, set[str]], expected: dict[int, set[str]]):
        self.assertEqual(len(actual), len(expected))
        for key, value in actual.items():
            self.assertIn(key, expected)
            self.assertSetEqual(value, expected[key])
