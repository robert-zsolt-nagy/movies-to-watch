import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.dao.authentication_manager import AuthenticationManager, AuthUser, BaseAccountInfo
from src.dao.m2w_graph_db_entities import User, TmdbUser
from src.dao.m2w_graph_db_repository_users import save_or_update_user, save_or_update_tmdb_user, get_one_user, \
    get_one_tmdb_user
from src.dao.tmdb_user_repository import TmdbUserRepository, TmdbRequestToken
from src.services.user_service import UserManagerService, EmailMismatchError, \
    PasswordMismatchError, WeakPasswordError
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase

TRAVIS_BELL_USER_DETAILS = {
    "avatar": {
        "gravatar": {
            "hash": "c9e9fc152ee756a900db85757c29815d"
        },
        "tmdb": {
            "avatar_path": "/xy44UvpbTgzs9kWmp4C3fEaCl5h.png"
        }
    },
    "id": 548,
    "iso_639_1": "en",
    "iso_3166_1": "CA",
    "name": "Travis Bell",
    "include_adult": False,
    "username": "travisbell"
}


class TestUserManagerService(M2wDatabaseTestCase):
    def test_get_m2w_user_profile_data_should_return_dict(self):
        # given
        user = User(
            user_id=uuid.uuid4().hex,
            nickname="Nick",
            email="nick@example.com",
            locale="US",
            profile_pic="00.png",
        )
        tmdb_user = TmdbUser(
            tmdb_id=1,
            username="nick-tmdb",
            user_id=user.user_id,
            name="",
            session="session-id",
            include_adult=True,
            iso_639_1="en",
            iso_3166_1="US"
        )
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=user)
        save_or_update_tmdb_user(tx=tx, user=tmdb_user)
        user.tmdb_user = tmdb_user
        tx.commit()
        under_test = self.create_user_manager_service()
        # when
        response = under_test.get_m2w_user_profile_data(user_id=user.user_id)
        # then
        self.assertEqual(response.user_id, user.user_id)
        self.assertEqual(response.nickname, user.nickname)
        self.assertEqual(response.email, user.email)
        self.assertEqual(response.locale, user.locale)
        self.assertEqual(response.profile_pic, user.profile_pic)
        self.assertEqual(response.tmdb_user.user_id, user.user_id)
        self.assertEqual(response.tmdb_user.tmdb_id, tmdb_user.tmdb_id)
        self.assertEqual(response.tmdb_user.username, tmdb_user.username)
        self.assertEqual(response.tmdb_user.name, tmdb_user.name)
        self.assertEqual(response.tmdb_user.session, tmdb_user.session)

    def test_get_firebase_user_account_info_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        last_refreshed = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        under_test.auth.get_account_info = MagicMock(return_value=BaseAccountInfo(
            email_verified=True,
            last_refresh_at=last_refreshed
        ))
        # when
        response = under_test.get_firebase_user_account_info(user_id_token="user_token")
        # then
        self.assertEqual(response.last_refresh_at, last_refreshed)
        self.assertEqual(response.email_verified, True)
        under_test.auth.get_account_info.assert_called_with(id_token="user_token")

    def test_sign_in_user_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        auth_user = AuthUser(
            user_id="user_id",
            email="email@example.com",
            display_name="display_name",
            id_token="id_token",
            refresh_token="refresh_token",
            expires_in=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        under_test.auth.sign_in_with_email_and_password = MagicMock(return_value=auth_user)
        # when
        response = under_test.sign_in_user(email=auth_user.email, password="pass")
        # then
        self.assertEqual(response, auth_user)
        under_test.auth.sign_in_with_email_and_password.assert_called_with(email=auth_user.email, password="pass")

    def test_update_user_data_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        under_test = self.create_user_manager_service()
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=User(
            user_id=self.user_id,
            profile_pic="wrong.png",
            nickname="name",
            email="email",
            locale="US"
        ))
        tx.commit()
        # when
        under_test.update_profile_picture(user_id=self.user_id, profile_pic="pic.png")
        # then
        tx = self.session.begin_transaction()
        saved = get_one_user(tx=tx, user_id=self.user_id)
        tx.commit()
        self.assertEqual(saved.profile_pic, "pic.png")
        self.assertEqual(saved.user_id, self.user_id)
        self.assertEqual(saved.nickname, "name")
        self.assertEqual(saved.email, "email")
        self.assertEqual(saved.locale, "US")

    def test_get_tmdb_account_data_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        under_test.user_repo.get_account_data = MagicMock(return_value=TRAVIS_BELL_USER_DETAILS)
        # when
        user_id = uuid.uuid4().hex
        response = under_test.get_tmdb_account_data(user_id=user_id, session_id="session")
        # then
        self.assertEqual(response.user_id, user_id)
        self.assertEqual(response.tmdb_id, 548)
        self.assertEqual(response.include_adult, False)
        self.assertEqual(response.iso_639_1, "en")
        self.assertEqual(response.iso_3166_1, "CA")
        self.assertEqual(response.username, "travisbell")
        self.assertEqual(response.name, "Travis Bell")
        under_test.user_repo.get_account_data.assert_called_with(session_id="session")

    def test_sign_in_and_update_tmdb_cache_should_return_dict(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        self.insert_tmdb_user_travis_bell()
        under_test.user_repo.get_account_data = MagicMock(return_value=TRAVIS_BELL_USER_DETAILS)
        auth_user = AuthUser(
            user_id=self.user_id,
            email="email",
            display_name="myName",
            id_token="myToken",
            refresh_token="myRefresh",
            expires_in=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        under_test.sign_in_user = MagicMock(return_value=auth_user)
        under_test.auth.get_account_info = MagicMock(return_value=BaseAccountInfo(
            email_verified=True,
            last_refresh_at="12:00"
        ))
        # when
        response = under_test.sign_in_and_update_tmdb_cache(email="email", password="pass")
        # then
        self.assertEqual(response, {
            'approve_id': None,
            'user': self.user_id,
            'email': "email",
            'nickname': "myName",
            'idToken': "myToken",
            'refreshToken': "myRefresh",
            'expiresIn': auth_user.expires_in,
            'emailVerified': True,
            'lastRefreshAt': "12:00"
        })
        under_test.sign_in_user.assert_called_with(email="email", password="pass")
        under_test.auth.get_account_info.assert_called_with(id_token="myToken")
        under_test.user_repo.get_account_data.assert_called_with(session_id="session")

    def test_update_tmdb_user_cache_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        self.insert_tmdb_user_travis_bell()
        under_test.user_repo.get_account_data = MagicMock(return_value=TRAVIS_BELL_USER_DETAILS)
        # when
        under_test.update_tmdb_user_cache(user_id=self.user_id)
        # then
        under_test.user_repo.get_account_data.assert_called_with(session_id="session")

    def test_update_tmdb_user_cache_should_pass_return_empty_if_tmdb_not_linked(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        # when
        under_test.update_tmdb_user_cache(user_id="user_id")
        # then
        # no exception

    def test_create_tmdb_session_for_user_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        token = TmdbRequestToken(
            success=True,
            request_token="request_token",
            expires_at=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        under_test.user_repo.create_session_id = MagicMock(return_value="session")
        under_test.user_repo.get_account_data = MagicMock(return_value=TRAVIS_BELL_USER_DETAILS)
        # when
        under_test.create_tmdb_session_for_user(user_id=self.user_id, request_token=token)
        # then
        tx = self.session.begin_transaction()
        tmdb_user = get_one_tmdb_user(tx=tx, user_id=self.user_id)
        tx.commit()
        self.assertEqual(tmdb_user.user_id, self.user_id)
        self.assertEqual(tmdb_user.tmdb_id, TRAVIS_BELL_USER_DETAILS['id'])
        under_test.user_repo.create_session_id.assert_called_with(request_token=token)

    def test_send_firebase_email_verification_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        under_test.auth.send_email_verification = MagicMock(return_value="success")
        # when
        response = under_test.send_firebase_email_verification(id_token="token")
        # then
        self.assertEqual(response, "success")
        under_test.auth.send_email_verification.assert_called_with(id_token="token")

    def test_sign_up_user_should_raise_error_on_email_mismatch(self):
        # given
        under_test = self.create_user_manager_service()
        # when
        with self.assertRaises(EmailMismatchError) as context:
            under_test.sign_up_user(email="a", confirm_email="b", password="", confirm_password="", nickname="")
        # then
        self.assertIsInstance(context.exception, EmailMismatchError)

    def test_sign_up_user_should_raise_error_on_password_mismatch(self):
        # given
        under_test = self.create_user_manager_service()
        # when
        with self.assertRaises(PasswordMismatchError) as context:
            under_test.sign_up_user(email="a", confirm_email="a", password="b", confirm_password="c", nickname="")

        # then
        self.assertIsInstance(context.exception, PasswordMismatchError)

    def test_sign_up_user_should_raise_error_on_weak_password(self):
        # given
        under_test = self.create_user_manager_service()
        # when
        with self.assertRaises(WeakPasswordError) as context:
            under_test.sign_up_user(email="a", confirm_email="a", password="b", confirm_password="b", nickname="")
        # then
        self.assertIsInstance(context.exception, WeakPasswordError)

    def test_sign_up_user_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        self.user_id = uuid.uuid4().hex
        auth_user = AuthUser(
            user_id=self.user_id,
            email="email",
            display_name="myName",
            id_token="myID",
            refresh_token="myRefresh",
            expires_in=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        under_test.auth.create_user_with_email_and_password = MagicMock(return_value=auth_user)
        under_test.auth.update_profile = MagicMock(return_value="success")
        under_test.send_firebase_email_verification = MagicMock(return_value="success")
        # when
        response = under_test.sign_up_user(
            email="e@mail.com",
            confirm_email="e@mail.com",
            password="password",
            confirm_password="password",
            nickname="Nick",
            picture="00.png",
            locale="XX"
        )
        # then
        self.assertEqual(response, True)
        under_test.auth.create_user_with_email_and_password.assert_called_with(email="e@mail.com", password="password")
        under_test.auth.update_profile.assert_called_with(id_token="myID", display_name="Nick")
        under_test.send_firebase_email_verification.assert_called_with(id_token="myID")
        actual = self.find_single_user(self.user_id)
        self.assertEqual(actual.user_id, self.user_id)
        self.assertEqual(actual.email, "e@mail.com")
        self.assertEqual(actual.nickname, "Nick")
        self.assertEqual(actual.profile_pic, "00.png")
        self.assertEqual(actual.locale, "XX")

    def test_get_tmdb_request_token_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        token = TmdbRequestToken(
            success=True,
            expires_at=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            request_token="my_token"
        )
        under_test.user_repo.create_request_token = MagicMock(return_value=token)
        # when
        response = under_test.get_tmdb_request_token()
        # then
        self.assertEqual(response, token)
        under_test.user_repo.create_request_token.assert_called_once()

    def test_get_tmdb_permission_url_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        token = TmdbRequestToken(
            success=True,
            expires_at=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            request_token="my_token"
        )
        under_test.user_repo.create_request_token = MagicMock(return_value=token)
        under_test.user_repo.get_user_permission_url = MagicMock(return_value="my_permission_URL")
        # when
        response = under_test.get_tmdb_permission_url(tmdb_request_token=token)
        # then
        self.assertEqual(response, "my_permission_URL")
        under_test.user_repo.get_user_permission_url.assert_called_with(
            redirect_to=None,
            tmdb_url="https://www.themoviedb.org",
            request_token=token
        )

    def create_user_manager_service(self) -> UserManagerService:
        under_test = UserManagerService(
            db=self.driver,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        return under_test

    def test_add_movie_to_users_watchlist_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        self.insert_tmdb_user_travis_bell()
        under_test.user_repo.add_movie_to_watchlist = MagicMock(
            return_value={"status_code": 1, "status_message": "Success.", "success": True})
        # when
        response = under_test.add_movie_to_users_watchlist(movie_id=1, user_id=self.user_id)
        # then
        self.assertEqual(response, True)
        under_test.user_repo.add_movie_to_watchlist.assert_called_with(
            movie_id=1,
            user_id=TRAVIS_BELL_USER_DETAILS['id'],
            session_id="session"
        )

    def test_remove_movie_from_users_watchlist_should_pass_correct_parameters(self):
        # given
        under_test = self.create_user_manager_service()
        self.insert_default_user_and_movie()
        self.insert_tmdb_user_travis_bell()
        under_test.user_repo.remove_movie_from_watchlist = MagicMock(
            return_value={"status_code": 1, "status_message": "Item removed.", "success": True})
        # when
        response = under_test.remove_movie_from_users_watchlist(movie_id=1, user_id=self.user_id)
        # then
        self.assertEqual(response, True)
        under_test.user_repo.remove_movie_from_watchlist.assert_called_with(
            movie_id=1,
            user_id=TRAVIS_BELL_USER_DETAILS['id'],
            session_id="session"
        )
