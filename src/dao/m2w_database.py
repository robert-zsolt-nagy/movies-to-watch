from google.cloud import firestore
from google.oauth2 import service_account

class M2WDatabaseException(Exception):
    """Base class for Exceptions of M2WDatabase"""
    def __init__(self, message: str):
        """Base class for Exceptions of M2WDatabase"""
        super().__init__(message)

class M2WDatabase():
    """Bundles the firestore related methods."""
    def __init__(self, project: str, credentials: service_account.Credentials) -> None:
        """Bundles the methods related to the 
        firestore database of movies-to-watch.

        Parameters
        ----------
        project: The project which the client acts on behalf of.
        credentials: The OAuth2 Credentials to use for this client.
        """
        self.__db = firestore.Client(project=project, credentials=credentials)

    def get_user(self, user_id: str) -> firestore.DocumentSnapshot:
        """Returns the user document with ID `user_id` if exists."""
        user_ref = self.__db.collection('users').document(user_id)
        user = user_ref.get()
        if user.exists:
            return user
        else:
            raise M2WDatabaseException("User does not exist.")