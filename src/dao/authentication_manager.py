from requests.exceptions import HTTPError
import json
import pyrebase
from typing import Union

class AuthenticationManager():
    """Provides the user authentication service."""
    def __init__(self, config: Union[dict, pyrebase.pyrebase.Auth]) -> None:
        """Provide user authentication service.
        
        Parameters
        ----------
        config: the configuration data for the firebase service as dictionary or 
        an instance of a pyrebase.Auth object.
        """
        if isinstance(config, dict):
            firebase_app = pyrebase.initialize_app(config=config)
            self.__auth = firebase_app.auth()
        else:
            self.__auth = config

    def get_authentication_error_msg(error: HTTPError) -> str:
        """Get the error message from a raised error. """
        message = json.loads(error.args[1])
        return message['error']["message"]
    
    def sign_in_with_email_and_password(self, email: str, password: str) -> dict:
        """Signs in a user with email and password.

        Parameters
        ----------
        email: the email of the user.
        password: the password of the user.
        
        Returns
        -------
        A user as dictionary.
        ```
        user
            'localId': str
            'email': str
            'displayName': str
            'idToken': str
            'refreshToken': str
            'expiresIn': str
        ```
        """
        return self.__auth.sign_in_with_email_and_password(email=email, password=password)
    
    def get_account_info(self, id_token: str) -> dict:
        """Gets the account information of a signed in user.

        Paramteres
        ----------
        id_token: the idToken of the signed in user.
        
        Returns
        -------
        ```
        Current info
            'createdAt': str
            'email': str
            'emailVerified': bool
            'lastLoginAt': str
            'lastRefreshAt': str 
            'localId': str 
            'passwordHash': str
            'passwordUpdatedAt': int 
            'providerUserInfo': [
                {
                    'email': str 
                    'federatedId': str 
                    'providerId': str 
                    'rawId': str
                }
            ], 
            'validSince': str
        ```
        """
        acc_info = self.__auth.get_account_info(id_token=id_token)
        return acc_info['users'][0]
    
    def create_user_with_email_and_password(self, email: str, password: str) -> dict:
        """Creates a new user with email and password.
        
        Returns
        -------
        The data of the creted user.
        ```
        User
            'displayName': str 
            'email': str 
            'expiresIn': str
            'idToken': str
            'kind': str
            'localId': str
            'refreshToken': str
            'registered': bool
        ```
        """
        return self.__auth.create_user_with_email_and_password(email=email, password=password)

    def update_profile(self, id_token, display_name = None, photo_url = None, delete_attribute = None):
        """Updates a profile with new data.
        
        Parameters
        ----------
        id_token: A Firebase Auth ID token for the user.
        display_name: User's new display name.
        photo_url: User's new photo url.
        delete_attribute: List of attributes to delete, "DISPLAY_NAME" or "PHOTO_URL". This will nullify these values.

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
        """Sends a password reset email to the provided email adress."""
        return self.__auth.send_password_reset_email(email=email)
