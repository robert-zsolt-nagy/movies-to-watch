from unittest import TestCase
from unittest.mock import MagicMock

from pyrebase.pyrebase import Auth
from requests.exceptions import HTTPError

from src.dao.authentication_manager import FirebaseAuthenticationManager


class TestAuthenticationManager(TestCase):
    def test_get_authentication_error_msg_returns_message(self):
        # given
        my_error = HTTPError("ignore", '{"error":{"message":"my error message"}}')

        # when
        message = FirebaseAuthenticationManager.get_authentication_error_msg(error=my_error)

        # then
        self.assertEqual(message, "my error message")

    def test_sign_in_with_email_and_password_should_return_data(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.sign_in_with_email_and_password = MagicMock(return_value={
            "user": {
                'localId': 'localId',
                'email': 'email',
                'displayName': 'displayName',
                'idToken': 'idToken',
                'refreshToken': 'refreshToken',
                'expiresIn': 'expiresIn'
            }
        })
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.sign_in_with_email_and_password(email="email", password="pass")

        # then
        auth.sign_in_with_email_and_password.assert_called_with(email="email", password="pass")
        self.assertEqual(response.user_id, 'localId')
        self.assertEqual(response.email, 'email')
        self.assertEqual(response.display_name, 'displayName')
        self.assertEqual(response.id_token, 'idToken')
        self.assertEqual(response.refresh_token, 'refreshToken')
        self.assertEqual(response.expires_in, 'expiresIn')


    def test_get_account_info_should_return_data(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.get_account_info = MagicMock(return_value={
            'kind': 'kind',
            'users': [
                {'createdAt': '1709835288954',
                 'displayName': 'name',
                 'email': 'mail',
                 'emailVerified': False,
                 'lastLoginAt': '1709836019146',
                 'lastRefreshAt': '2024-03-07T18:26:59.146Z',
                 'localId': 'id',
                 'passwordHash': 'hash',
                 'passwordUpdatedAt': 1709835288954,
                 'providerUserInfo': [
                     {'displayName': 'name',
                      'email': 'mail',
                      'federatedId': 'id',
                      'providerId': 'password',
                      'rawId': 'mail'}
                 ],
                 'validSince': '1709835288'}
            ]
        })
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.get_account_info(id_token="ignore")

        # then
        auth.get_account_info.assert_called_with(id_token="ignore")
        self.assertEqual(response.email_verified, False)
        self.assertEqual(response.last_refresh_at, '2024-03-07T18:26:59.146Z')


    def test_create_user_with_email_and_password_should_return_data(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.create_user_with_email_and_password = MagicMock(return_value={
            "user": {
                'localId': 'localId',
                'email': 'email',
                'displayName': 'displayName',
                'idToken': 'idToken',
                'refreshToken': 'refreshToken',
                'expiresIn': 'expiresIn'
            }
        })
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.create_user_with_email_and_password(email="email", password="pass")

        # then
        auth.create_user_with_email_and_password.assert_called_with(email="email", password="pass")
        self.assertEqual(response.user_id, 'localId')
        self.assertEqual(response.email, 'email')
        self.assertEqual(response.display_name, 'displayName')
        self.assertEqual(response.id_token, 'idToken')
        self.assertEqual(response.refresh_token, 'refreshToken')
        self.assertEqual(response.expires_in, 'expiresIn')


    def test_update_profile_should_pass_on_information(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.update_profile = MagicMock(return_value=True)
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.update_profile(id_token="id", display_name="name", photo_url="/pic.jpg")

        # then
        self.assertEqual(response, True)
        auth.update_profile.assert_called_with(id_token="id", display_name="name", photo_url="/pic.jpg",
                                               delete_attribute=None)


    def test_send_email_verification_should_pass_on_information(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.send_email_verification = MagicMock(return_value=True)
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.send_email_verification(id_token="id")

        # then
        self.assertEqual(response, True)
        auth.send_email_verification.assert_called_with(id_token="id")


    def test_send_password_reset_email_should_pass_on_information(self):
        # given
        auth = Auth(api_key="ignore", requests=None, credentials="ignore")
        auth.send_password_reset_email = MagicMock(return_value=True)
        under_test = FirebaseAuthenticationManager(config=auth)

        # when
        response = under_test.send_password_reset_email(email="mail")

        # then
        self.assertEqual(response, True)
        auth.send_password_reset_email.assert_called_with(email="mail")
