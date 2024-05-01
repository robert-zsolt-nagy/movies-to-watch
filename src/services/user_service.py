from src.dao.m2w_database import M2WDatabase
from src.dao.authentication_manager import AuthenticationManager
from src.dao.tmdb_user_repository import TmdbUserRepository
from requests.exceptions import HTTPError


class UserManagerException(Exception):
    """Base class for exceptions in the User Manager Service."""
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

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
            except:
                raise UserManagerException("Error during reading TMDB account data.")            
            else:
                data = {
                    "tmdb_user":fresh_data
                }
                self.update_user_data(user_id=user_id, user_data=data)
        else:
            return {}
        
    def create_tmdb_session_for_user(self, request_token: dict):
        """ Create a session id for a particular request token of a user.
        
        Parameters
        ----------
        request_token: the response received after requesting a new token for the user.

        Returns
        -------
        The created session ID.
        """
        return self.user_repo.create_session_id(request_token=request_token)


# create user if signup form is validated
# link to tmdb
# resend email verification for user