from src.dao.m2w_database import M2WDatabase
from src.dao.authentication_manager import AuthenticationManager
from src.dao.tmdb_user_repository import TmdbUserRepository
from requests.exceptions import HTTPError
from typing import Optional
from google.cloud import firestore


class UserManagerException(Exception):
    """Base class for exceptions in the User Manager Service."""

class EmailMismatchError(UserManagerException):
    """Email and confirm Email does not match."""

class PasswordMismatchError(UserManagerException):
    """Password and confirm password does not natch."""

class WeakPasswordError(UserManagerException):
    """Password should contain at least 6 characters."""


class UserManagerService():
    """Handles the user administration."""
    def __init__(
            self, 
            m2w_db: M2WDatabase,
            auth: AuthenticationManager,
            user_repo: TmdbUserRepository
            ) -> None:
        """Handles the user administration.
        
        Parameters
        ----------
        m2w_db: object that bundles the M2W Database methods.
        auth: object that provides the authentication service.
        user_repo: object that bundles the user related TMDB requests.
        """
        self.user_handler = m2w_db.user
        self.auth = auth
        self.user_repo = user_repo

    def get_m2w_user_profile_data(self, user_id: str) -> dict:
        """Get the cached profile data for the user.
        
        Parameters
        ----------
        user_id: the M2W ID of the user.

        Returns
        -------
        The cached profile data as dict.

        Raises
        ------
        M2WDatabaseException: if document doesn't exist.
        """
        user = self.user_handler.get_one(id_=user_id)
        profile_data = user.to_dict()
        return profile_data
    
    def get_firebase_user_account_info(self, user_idtoken: str) -> dict:
        """Get the firebase account info for user.
        
        Paramteres
        ----------
        user_idtoken: the idToken of the signed in user.

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
        result = self.auth.get_account_info(id_token=user_idtoken)
        return result
    
    def sign_in_user(self, email: str, password: str) -> dict:
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
        return self.auth.sign_in_with_email_and_password(email=email, password=password)
    
    def update_user_data(self, user_id: str, user_data: dict):
        """Creates or updates a user.
        If the user exists merges the data with the existing content.
        
        Parameters
        ----------
        user_id: the ID of the document in the database.
        user_data: a dictionary containing the data fields of the document.
        """
        return self.user_handler.set_data(id_=user_id, data=user_data)
    
    def get_tmdb_account_data(self, session_id: str) -> dict:
        """ Gets the account data of a TMDB user.
        
        Parameters
        ----------
            session_id: the current session ID.

        Returns
        -------
            The received response as a dictionary that contains the account's data.
        """
        return self.user_repo.get_account_data(session_id=session_id)
    
    def sign_in_and_update_tmdb_cache(self, email: str, password: str) -> dict:
        """Signs in the user and updates the tmdb cache if necessary.

        Parameters
        ----------
        email: the email of the user.
        password: the password of the user.
        
        Returns
        -------
        The user data for session as dict.

        Raises
        ------
        UserManagerException in case of firebase errors during requests.
        """
        try:
            user = self.sign_in_user(email=email, password=password)
            response = {
                'approve_id': None
            }
            response['user'] = user['localId']
            response['email'] = user['email']
            response['nickname'] = user['displayName']
            response['idToken'] = user['idToken']
            response['refreshToken'] = user['refreshToken']
            response['expiresIn'] = user['expiresIn']

            account_info = self.get_firebase_user_account_info(user['idToken'])
            response['emailVerified'] = account_info['emailVerified']
            response['lastRefreshAt'] = account_info['lastRefreshAt']

            self.update_tmdb_user_cache(user_id=response['user'])
        except HTTPError as he:
            msg = self.auth.get_authentication_error_msg(he)
            raise UserManagerException(msg)
        else:
            return response

    def update_tmdb_user_cache(self, user_id: str) -> dict:
        """Update the TMDB related data of user in the M2W database.
        
        Parameters
        ----------
        user_id: the ID of the user in M2W database.

        Returns
        -------
        The TMDB data written in the cache.
        """
        user = self.user_handler.get_one(id_=user_id)
        user_data = user.to_dict()
        if user_data['tmdb_session'] is not None:
            try:
                fresh_data = self.get_tmdb_account_data(session_id=user_data['tmdb_session'])
            except Exception:
                raise UserManagerException("Error during reading TMDB account data.")            
            else:
                data = {
                    "tmdb_user":fresh_data
                }
                self.update_user_data(user_id=user_id, user_data=data)
                return data
        else:
            return {}
        
    def create_tmdb_session_for_user(self, request_token: dict) -> str:
        """ Create a session id for a particular request token of a user.
        
        Parameters
        ----------
        request_token: the response received after requesting a new token for the user.

        Returns
        -------
        The created session ID.
        """
        return self.user_repo.create_session_id(request_token=request_token)
    
    def send_firebase_email_verification(self, id_token: str):
        """Send a new verification email for the user identified by id_token.
        
        Parameters
        ----------
        id_token: the ID token of the user who needs a verfication email.
        """
        return self.auth.send_email_verification(id_token=id_token)
    
    def sign_up_user(
            self,
            email: str,
            confirm_email: str,
            password: str,
            confirm_password: str,
            nickname: str,
            picture: str="01.png",
            locale: str="HU"
        ) -> bool:
        """Validate the sign up form and creeate the user if valid.
        
        Parameters
        ----------
        email: the email of the user.
        confirm_email: the email of the user repeated.
        password: the password of the user.
        confirm_password: the password of the user repeated.
        nickname: the nickname of the user.
        picture: the filename of the chosen profile picture.
        locale: the two character locale ID of the user's locale.

        Returns
        -------
        True if successful.

        Raises
        ------
        EmailMismatchError: if email and confirm_email doesn't match.
        PasswordMismatchError: if password and confirm_password doesn't match.
        WeakPasswordError: if password is shorter than 6 characters.
        HttpError: if firebase raises INVALID_EMAIL, MISSING_PASSWORD, INVALID_LOGIN_CREDENTIALS, 
        EMAIL_EXISTS or WEAK_PASSWORD

        """
        if email != confirm_email:
            raise EmailMismatchError()
        
        if password != confirm_password:
            raise PasswordMismatchError()
        
        if len(password) < 6:
            raise WeakPasswordError()
        
        # create user and add details
        my_user = self.auth.create_user_with_email_and_password(
            email=email,
            password=password
        )
        self.auth.update_profile(
            id_token=my_user['idToken'],
            display_name=nickname
        )
        # send verification email for profile
        self.send_firebase_email_verification(id_token=my_user['idToken'])
        # upsert user profile in M2W database
        data = {
            "email": email, 
            "nickname": nickname, 
            "tmdb_user": None,
            "tmdb_session": None,
            "locale": locale,
            "primary_group": None,
            "profile_pic": picture
            }
        self.user_handler.set_data(
            id_=my_user['localId'],
            data=data
        )
        return True
        
    def init_link_user_profile_to_tmdb(
            self,
            redirect_to: Optional[str] = None, 
            tmdb_url: str = "https://www.themoviedb.org",
            ) -> dict:
        """Initiate linking user's M2W and TMDB profiles.
        
        Parameters
        ----------
        redirect_to: the URL to redirect to after the approval process.
        tmdb_url: the base URL of TMDB.

        Returns
        -------
        The created tmdb request token and user permission URL in a dict.
        ```
        {
            "tmdb_request_token": str,
            "permission_URL" : str
        }
        ```
        """
        tmdb_request_token = self.user_repo.create_request_token()
        permission_URL = self.user_repo.get_user_permission_URL(
            redirect_to=redirect_to,
            tmdb_url=tmdb_url,
            **tmdb_request_token
        )
        return {
            "tmdb_request_token": tmdb_request_token, 
            "permission_URL": permission_URL
        }
    
    def add_movie_to_users_watchlist(self, movie_id: str, user_id: str) -> bool:
        """Adds a movie to the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: the ID of the movie in M2W.
        user_id: the M2W ID of the user.

        Returns
        --------
        True if successful, False otherwise.
        
        """
        # get user data
        try:
            user_data = self.get_m2w_user_profile_data(user_id=user_id)
            response_watchlist = self.user_repo.add_movie_to_watchlist(
                movie_id=int(movie_id),
                user_id=user_data['tmdb_user']['id'],
                session_id=user_data['tmdb_session']
            )
        except KeyError:
            raise UserManagerException("TMDB data of user is missing.")
        else:
            return response_watchlist["success"]
        
    def remove_movie_from_users_watchlist(self, movie_id: str, user_id: str) -> bool:
        """Remove a movie from the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: the ID of the movie in M2W.
        user_id: the M2W ID of the user.

        Returns
        --------
        True if successful, False otherwise.
        
        """
        try:
            user_data = self.get_m2w_user_profile_data(user_id=user_id)
            response_watchlist = self.user_repo.remove_movie_from_watchlist(
                movie_id=int(movie_id),
                user_id=user_data['tmdb_user']['id'],
                session_id=user_data['tmdb_session']
            )
        except KeyError:
            raise UserManagerException("TMDB data of user is missing.")
        else:
            return response_watchlist["success"]
        
    def get_blocklist(self, user_id: str) -> firestore.CollectionReference:
        """Returns the reference to the blocklist collection of a user 
        with ID `user_id` if the user exists.
        
        Raises
        ------
        M2WDatabaseException: if user doesn't exist.
        """
        return self.user_handler.get_blocklist(user_id=user_id)

    def get_movies_watchlist(self, user_id: str) -> list[dict]:
        """Get the movies watchlist of the user.
        
        Parameters
        ----------
        user_id: the ID of the user in M2W Database.

        Returns
        -------
        A list containing the movie dicitonaries.
        """
        try:
            user_data = self.get_m2w_user_profile_data(user_id=user_id)
            watchlist = self.user_repo.get_watchlist_movie(
                user_id=user_data['tmdb_user']['id'],
                session_id=user_data['tmdb_session']
            )
        except KeyError:
            raise UserManagerException("TMDB data of user is missing.")
        else:
            return watchlist
        
