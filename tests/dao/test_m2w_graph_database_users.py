import uuid

from src.dao.m2w_graph_db_entities import TmdbUser, User
from src.dao.m2w_graph_db_repository_users import save_or_update_user, save_or_update_tmdb_user, count_tmdb_users, \
    get_tmdb_users
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase, get_john_doe


class TestM2wGraphDatabaseUsers(M2wDatabaseTestCase):

    def test_save_or_update_user_should_save_details_for_sign_up(self):
        # given
        self.insert_default_user_and_movie()
        to_save = get_john_doe()
        # when
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=to_save)
        tx.commit()
        # then
        actual = self.find_single_user(user_id=to_save.user_id)
        self.assert_user_equals(actual, to_save)

    def test_save_or_update_tmdb_user_should_save_details_when_tmdb_is_connected(self):
        # given
        self.insert_default_user_and_movie()
        to_save = TmdbUser(
            user_id=self.user_id,
            tmdb_id=1,
            iso_3166_1="HU",
            iso_639_1="en",
            include_adult=False,
            username="johndoe",
            session=uuid.uuid4().hex
        )
        # when
        tx = self.session.begin_transaction()
        save_or_update_tmdb_user(tx=tx, user=to_save)
        tx.commit()
        # then
        actual = self.find_single_tmdb_user(user_id=to_save.user_id)
        self.assert_tmdb_user_equals(actual, to_save)

    def test_get_tmdb_users_should_return_one_page_when_available(self):
        # given
        self.insert_default_user_and_movie()
        jane = User(
            user_id=uuid.uuid4().hex,
            nickname="janedoe",
            email="janedoe@example.com",
            locale="HU",
            profile_pic="10.png"
        )
        to_save_1 = TmdbUser(
            user_id=self.user_id,
            tmdb_id=1,
            iso_3166_1="HU",
            iso_639_1="en",
            include_adult=False,
            username="johndoe",
            session=uuid.uuid4().hex
        )
        to_save_2 = TmdbUser(
            user_id=jane.user_id,
            tmdb_id=2,
            iso_3166_1="HU",
            iso_639_1="en",
            include_adult=False,
            username="janedoe",
            session=uuid.uuid4().hex
        )
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=jane)
        save_or_update_tmdb_user(tx=tx, user=to_save_1)
        save_or_update_tmdb_user(tx=tx, user=to_save_2)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual_count = count_tmdb_users(tx=tx)
        actual_page_1 = get_tmdb_users(tx=tx, offset=0, limit=1)
        actual_page_2 = get_tmdb_users(tx=tx, offset=1, limit=1)
        actual_page_3 = get_tmdb_users(tx=tx, offset=2, limit=1)
        actual_all = get_tmdb_users(tx=tx, offset=0, limit=5)
        tx.commit()
        # then
        self.assertEqual(actual_count, 2)
        self.assertEqual(len(actual_page_1), 1)
        self.assertEqual(len(actual_page_2), 1)
        self.assertEqual(len(actual_page_3), 0)
        self.assertEqual(len(actual_all), 2)
        self.assert_tmdb_user_equals(actual_page_1[0], to_save_1)
        self.assert_tmdb_user_equals(actual_page_2[0], to_save_2)
        self.assert_tmdb_user_equals(actual_all[0], to_save_1)
        self.assert_tmdb_user_equals(actual_all[1], to_save_2)
