from src.dao.m2w_database import M2WDatabase
from src.dao.authentication_manager import AuthenticationManager
from src.dao.tmdb_user_repository import TmdbUserRepository

# sign in with email and fill user data in session
# update tmdb data for user
# create user if signup form is validated
# create tmdb session id and cache tmdb data for user
# return profile data by id
# link to tmdb
# resend email verification for user

class UserManagerService():
    """Handles the user administration."""
    def __init__(
            self, 
            m2w_db: M2WDatabase,
            auth: AuthenticationManager,
            user_repo: TmdbUserRepository
            ) -> None:
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
    
    def sign_in_user(self, email: str, password: str):
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
    
    def sign_in_and_update_tmdb_cache(self) -> dict:
        """Signs in the user and updates the tmdb cache if necessary.
        
        Returns
        -------
        The user data for session as dict.
        """
        user = self.sign_in_user(email="", password="")
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

        return response

    def update_tmdb_user_cache(self, user_id: str) -> bool:
        user = self.user_handler.get_one(id_=user_id)
        user_data = user.to_dict()
        if user_data['tmdb_session'] is not None:
            try:
                fresh_data = self.user_repo.get_account_data(session_id=user_data['tmdb_session'])
            except:
                pass
            else:
                data = {
                    "tmdb_user":fresh_data
                }
                self.update_user_data(user_id=user_id, user_data=data)
