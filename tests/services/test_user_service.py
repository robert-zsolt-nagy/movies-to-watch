from unittest import TestCase
from unittest.mock import MagicMock

from src.services.user_service import UserManagerException, UserManagerService, EmailMismatchError, PasswordMismatchError, WeakPasswordError
from src.dao.tmdb_user_repository import TmdbUserRepository
from src.dao.m2w_database import M2WDatabase, M2wUserHandler
from src.dao.authentication_manager import AuthenticationManager

class TestUserManagerService(TestCase):
    def test_get_m2w_user_profile_data_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        user = MagicMock()
        user.to_dict = MagicMock(return_value={"profile": "data"})
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.user_handler = MagicMock(M2wUserHandler)
        under_test.user_handler.get_one = MagicMock(return_value=user)

        #when
        response = under_test.get_m2w_user_profile_data(user_id="user_1")

        #then
        self.assertEqual(response, {"profile": "data"})
        under_test.user_handler.get_one.assert_called_with(id_="user_1")

    def test_get_firebase_user_account_info_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.auth.get_account_info = MagicMock(return_value={"acccount":"info"})

        #when
        response = under_test.get_firebase_user_account_info(user_idtoken="user_token")

        #then
        self.assertEqual(response, {"acccount":"info"})
        under_test.auth.get_account_info.assert_called_with(id_token="user_token")

    def test_sign_in_user_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.auth.sign_in_with_email_and_password = MagicMock(return_value={"user":"data"})

        #when
        response = under_test.sign_in_user(email="email", password="pass")

        #then
        self.assertEqual(response, {"user":"data"})
        under_test.auth.sign_in_with_email_and_password.assert_called_with(email="email", password="pass")
    
    def test_update_user_data_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.user_handler = MagicMock(M2wUserHandler)
        under_test.user_handler.set_data = MagicMock(return_value="success")

        #when
        response = under_test.update_user_data(user_id="user_id", user_data={"user":"data"})

        #then
        self.assertEqual(response, "success")
        under_test.user_handler.set_data.assert_called_with(id_="user_id", data={"user":"data"})

    def test_get_tmdb_account_data_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.user_repo.get_account_data = MagicMock(return_value={"account":"data"})

        #when
        response = under_test.get_tmdb_account_data(session_id="session")

        #then
        self.assertEqual(response, {"account":"data"})
        under_test.user_repo.get_account_data.assert_called_with(session_id="session")
    
    def test_sign_in_and_update_tmdb_cache_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.sign_in_user = MagicMock(return_value={
            'localId':"myID",
            'email':"myMail",
            'displayName':"myName",
            'idToken':"myToken",
            'refreshToken':"myRefresh",
            'expiresIn': 1000
        })
        under_test.get_firebase_user_account_info = MagicMock(return_value={
            'emailVerified':True,
            'lastRefreshAt':"12:00"
        })
        under_test.update_tmdb_user_cache = MagicMock(return_value="updated")

        #when
        response = under_test.sign_in_and_update_tmdb_cache(email="email", password="pass")

        #then
        self.assertEqual(response, {
            'approve_id': None,
            'user':"myID",
            'email':"myMail",
            'nickname':"myName",
            'idToken':"myToken",
            'refreshToken':"myRefresh",
            'expiresIn': 1000,
            'emailVerified':True,
            'lastRefreshAt':"12:00"
        })
        under_test.sign_in_user.assert_called_with(email="email", password="pass")
        under_test.get_firebase_user_account_info.assert_called_with("myToken")
        under_test.update_tmdb_user_cache.assert_called_with(user_id="myID")

    def test_update_tmdb_user_cache_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        user = MagicMock()
        user.to_dict = MagicMock(return_value={'tmdb_session': "session"})
        under_test.user_handler.get_one = MagicMock(return_value=user)
        under_test.get_tmdb_account_data = MagicMock(return_value={
            "tmdb_id":1,
            "tmdb_username":"t_user"
        })
        under_test.update_user_data = MagicMock(return_value="updated")

        #when
        response = under_test.update_tmdb_user_cache(user_id="user_id")

        #then
        self.assertEqual(response, {
            "tmdb_user":{
                "tmdb_id":1,
                "tmdb_username":"t_user"
            }
        })
        under_test.user_handler.get_one.assert_called_with(id_="user_id")
        under_test.get_tmdb_account_data.assert_called_with(session_id="session")
        under_test.update_user_data.assert_called_with(user_id="user_id", user_data={
            "tmdb_user":{
                "tmdb_id":1,
                "tmdb_username":"t_user"
            }
        })

    def test_update_tmdb_user_cache_should_pass_return_empty_if_tmdb_not_linked(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        user = MagicMock()
        user.to_dict = MagicMock(return_value={'tmdb_session': None})
        under_test.user_handler.get_one = MagicMock(return_value=user)

        #when
        response = under_test.update_tmdb_user_cache(user_id="user_id")

        #then
        self.assertEqual(response, {})
        under_test.user_handler.get_one.assert_called_with(id_="user_id")

    def test_update_tmdb_user_cache_should_raise_exception_on_error(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        user = MagicMock()
        user.to_dict = MagicMock(return_value={'tmdb_session': "session"})
        under_test.user_handler.get_one = MagicMock(return_value=user)
        def raiser(*args, **kwargs):
            raise Exception("Some error.")
        under_test.get_tmdb_account_data = MagicMock(side_effect=raiser)

        #when
        with self.assertRaises(UserManagerException) as context:
            under_test.update_tmdb_user_cache(user_id="user_id")

        #then
        under_test.user_handler.get_one.assert_called_with(id_="user_id")
        self.assertIsInstance(context.exception, UserManagerException)

    def test_create_tmdb_session_for_user_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.user_repo.create_session_id = MagicMock(return_value="success")

        #when
        response = under_test.create_tmdb_session_for_user(request_token={"request":"token"})

        #then
        self.assertEqual(response, "success")
        under_test.user_repo.create_session_id.assert_called_with(request_token={"request":"token"})

    def test_send_firebase_email_verification_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.auth.send_email_verification = MagicMock(return_value="success")

        #when
        response = under_test.send_firebase_email_verification(id_token="token")

        #then
        self.assertEqual(response, "success")
        under_test.auth.send_email_verification.assert_called_with(id_token="token")
        
    def test_sign_up_user_should_raise_error_on_email_mismatch(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )

        #when
        with self.assertRaises(EmailMismatchError) as context:
            under_test.sign_up_user(email="a", confirm_email="b", password="", confirm_password="", nickname="")

        #then
        self.assertIsInstance(context.exception, EmailMismatchError)

    def test_sign_up_user_should_raise_error_on_password_mismatch(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )

        #when
        with self.assertRaises(PasswordMismatchError) as context:
            under_test.sign_up_user(email="a", confirm_email="a", password="b", confirm_password="c", nickname="")

        #then
        self.assertIsInstance(context.exception, PasswordMismatchError)

    def test_sign_up_user_should_raise_error_on_weak_password(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )

        #when
        with self.assertRaises(WeakPasswordError) as context:
            under_test.sign_up_user(email="a", confirm_email="a", password="b", confirm_password="b", nickname="")

        #then
        self.assertIsInstance(context.exception, WeakPasswordError)

    def test_sign_up_user_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.auth.create_user_with_email_and_password = MagicMock(return_value={
            'idToken':"myID",
            'localId':'myLocalID'
        })
        under_test.auth.update_profile = MagicMock(return_value="success")
        under_test.send_firebase_email_verification = MagicMock(return_value="success")
        under_test.user_handler.set_data = MagicMock(return_value="succcess")

        #when
        response = under_test.sign_up_user(
            email="e@mail.com", 
            confirm_email="e@mail.com", 
            password="password", 
            confirm_password="password", 
            nickname="Nick",
            picture="00.png",
            locale="XX"
        )

        #then
        self.assertEqual(response, True)
        under_test.auth.create_user_with_email_and_password.assert_called_with(email="e@mail.com", password="password")
        under_test.auth.update_profile.assert_called_with(id_token="myID", display_name="Nick")
        under_test.send_firebase_email_verification.assert_called_with(id_token="myID")
        under_test.user_handler.set_data.assert_called_with(id_='myLocalID',data={
            "email": "e@mail.com", 
            "nickname": "Nick", 
            "tmdb_user": None,
            "tmdb_session": None,
            "locale": "XX",
            "primary_group": None,
            "profile_pic": "00.png"
        })
    
    def test_init_link_user_profile_to_tmdb_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.user = MagicMock(M2wUserHandler)
        under_test = UserManagerService(
            m2w_db=m2w_db,
            auth=MagicMock(AuthenticationManager),
            user_repo=MagicMock(TmdbUserRepository)
        )
        under_test.user_repo.create_request_token = MagicMock(return_value={
            "success": True, 
            "expires_at": "2024-05-06", 
            "request_token": "my_token"})
        under_test.user_repo.get_user_permission_URL = MagicMock(return_value="my_permission_URL")

        #when
        response = under_test.init_link_user_profile_to_tmdb()

        #then
        self.assertEqual(response, {
            "permission_URL": "my_permission_URL", 
            "tmdb_request_token":{
                "success": True, 
                "expires_at": "2024-05-06", 
                "request_token": "my_token"}
            })
        under_test.user_repo.create_request_token.assert_called_once()
        under_test.user_repo.get_user_permission_URL.assert_called_with(
            redirect_to=None,
            tmdb_url="https://www.themoviedb.org",
            success=True,
            expires_at="2024-05-06",
            request_token="my_token"
        )
        
