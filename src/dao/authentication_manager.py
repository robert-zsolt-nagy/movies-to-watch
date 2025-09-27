import logging

from neo4j import Record
from requests.exceptions import HTTPError
import json
import pyrebase
from typing import Union

from src.services.user_service import UserManagerException


class BaseAccountInfo:
    def __init__(self, email_verified: bool, last_refresh_at: str) -> None:
        self.email_verified = email_verified
        self.last_refresh_at = last_refresh_at

class AuthUser:
    def __init__(self, user_id: str, email: str, display_name: str, id_token: str,
                 refresh_token: str, expires_in: str | int) -> None:
        self.user_id = user_id
        self.email = email
        self.display_name = display_name
        self.id_token = id_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in

    @classmethod
    def from_response(cls, response: dict):
        user = response
        return cls(
            user_id=user["localId"],
            email=user["email"],
            display_name=user["displayName"],
            id_token=user["idToken"],
            refresh_token=user["refreshToken"],
            expires_in=user["expiresIn"]
        )

    @classmethod
    def from_record(cls, record: Record):
        return cls(
            user_id=record["user_id"],
            email=record["email"],
            display_name=record["display_name"],
            id_token=record["id_token"],
            refresh_token=record["refresh_token"],
            expires_in=record["expires_in"]
        )

    def to_dict(self, account_info: BaseAccountInfo):
        return {
            'approve_id': None,
            'user': self.user_id,
            'email': self.email,
            'nickname': self.display_name,
            'idToken': self.id_token,
            'refreshToken': self.refresh_token,
            'expiresIn': self.expires_in,
            'emailVerified': account_info.email_verified,
            'lastRefreshAt': account_info.last_refresh_at
        }


class AuthenticationManager:
    """Provides the user authentication service."""

    @staticmethod
    def get_authentication_error_msg(error: HTTPError) -> str:
        """Get the error message from a raised error. """
        message = json.loads(error.args[1])
        return message['error']["message"]

    def sign_in_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Signs in a user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.

        Returns
        -------
        AuthUser
            An authenticated user.
        """
        pass

    def get_account_info(self, id_token: str) -> BaseAccountInfo:
        """Gets the account information of a signed-in user.

        Parameters
        ----------
        id_token: str
            the idToken of the signed-in user.

        Returns
        -------
        BaseAccountInfo
            The most crucial account information.
        """
        pass

    def create_user_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Creates a new user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.

        Returns
        -------
        AuthUser
            The data of the created user.
        """
        pass

    def update_profile(self, id_token, display_name=None, photo_url=None, delete_attribute=None):
        """Updates a profile with new data.

        Parameters
        ----------
        id_token:
            A Firebase Auth ID token for the user.
        display_name:
            User's new display name.
        photo_url:
            User's new photo url.
        delete_attribute:
            List of attributes to delete, "DISPLAY_NAME" or "PHOTO_URL". This will nullify these values.

        """
        pass

    def send_email_verification(self, id_token):
        """Sends a new verification email for the user identified by id_token."""
        pass

    def send_password_reset_email(self, email):
        """Sends a password reset email to the provided email address."""
        pass

class FirebaseAuthenticationManager(AuthenticationManager):
    """Provides the user authentication service."""
    def __init__(self, config: Union[dict, pyrebase.pyrebase.Auth]) -> None:
        """Provide user authentication service.
        
        Parameters
        ----------
        config:
            the configuration data for the firebase service as a dictionary or
            an instance of a pyrebase.Auth object.
        """
        if isinstance(config, dict):
            firebase_app = pyrebase.initialize_app(config=config)
            self.__auth = firebase_app.auth()
        else:
            self.__auth = config
    
    def sign_in_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Signs in a user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.
        
        Returns
        -------
        AuthUser
            An authenticated user.

        Raises
        ------
        UserManagerException
            If the authentication fails.
        """
        try:
            response = self.__auth.sign_in_with_email_and_password(email=email, password=password)
            return AuthUser.from_response(response)
        except Exception as e:
            logging.error(f"Error signing in: {e}")
            raise UserManagerException("Error signing in")
    
    def get_account_info(self, id_token: str) -> BaseAccountInfo:
        """Gets the account information of a signed-in user.

        Parameters
        ----------
        id_token: str
            the idToken of the signed-in user.
        
        Returns
        -------
        BaseAccountInfo
            The most crucial account information.
        """
        acc_info = self.__auth.get_account_info(id_token=id_token)
        first_acc = acc_info['users'][0]
        return BaseAccountInfo(
            email_verified=first_acc['emailVerified'],
            last_refresh_at=first_acc['lastRefreshAt']
        )
    
    def create_user_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Creates a new user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.

        Returns
        -------
        AuthUser
            The data of the created user.
        """
        try:
            response = self.__auth.create_user_with_email_and_password(email=email, password=password)
            return AuthUser.from_response(response)
        except Exception as e:
            logging.error(f"Error creating user: {e}")
            raise UserManagerException("Error creating user.")

    def update_profile(self, id_token, display_name = None, photo_url = None, delete_attribute = None):
        """Updates a profile with new data.
        
        Parameters
        ----------
        id_token:
            A Firebase Auth ID token for the user.
        display_name:
            User's new display name.
        photo_url:
            User's new photo url.
        delete_attribute:
            List of attributes to delete, "DISPLAY_NAME" or "PHOTO_URL". This will nullify these values.

        """
        return self.__auth.update_profile(
            id_token=id_token,
            display_name=display_name,
            photo_url=photo_url,
            delete_attribute=delete_attribute
            )

    def send_email_verification(self, id_token):
        """Sends a new verification email for the user identified by id_token."""
        return self.__auth.send_email_verification(id_token=id_token)
    
    def send_password_reset_email(self, email):
        """Sends a password reset email to the provided email address."""
        return self.__auth.send_password_reset_email(email=email)
