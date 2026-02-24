from requests.exceptions import HTTPError

from src.dao.m2w_graph_db_repository_auth import Neo4jAuthenticationManager
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase


class TestAuthenticationManager(M2wDatabaseTestCase):
    def test_get_authentication_error_msg_returns_message(self):
        # given
        my_error = HTTPError("ignore", '{"error":{"message":"my error message"}}')

        # when
        message = Neo4jAuthenticationManager.get_authentication_error_msg(error=my_error)

        # then
        self.assertEqual(message, "my error message")


    def test_create_user_with_email_and_password_should_return_data(self):
        # given
        under_test = Neo4jAuthenticationManager(self.driver)

        # when
        response = under_test.create_user_with_email_and_password(email="email", password="pass")

        # then
        self.assertIsNotNone(response.user_id)
        self.assertEqual(response.email, 'email')
        self.assertEqual(response.display_name, 'email')
        self.assertEqual(response.id_token, response.user_id)
        self.assertEqual(response.refresh_token, 'refresh_token')
        self.assertEqual(response.expires_in, 3600)


    def test_update_profile_should_pass_on_information(self):
        # given
        under_test = Neo4jAuthenticationManager(self.driver)
        user = under_test.create_user_with_email_and_password(email="email", password="pass")

        # when
        under_test.update_profile(id_token=user.id_token, display_name="name", photo_url="/pic.jpg")

        # then
        info = under_test.sign_in_with_email_and_password(email="email", password="pass")
        self.assertEqual(info.display_name, "name")

    def test_send_email_verification_should_pass_on_information(self):
        # given
        under_test = Neo4jAuthenticationManager(self.driver)

        # when
        response = under_test.send_email_verification(id_token="id")

        # then
        self.assertEqual(response, True)


    def test_send_password_reset_email_should_pass_on_information(self):
        # given
        under_test = Neo4jAuthenticationManager(self.driver)

        # when
        response = under_test.send_password_reset_email(email="mail")

        # then
        self.assertEqual(response, True)
