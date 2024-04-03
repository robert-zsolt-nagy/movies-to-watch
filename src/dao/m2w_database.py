from google.cloud import firestore
from google.oauth2 import service_account
from typing import Generator, Optional

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

    @property
    def database(self) -> firestore.Client:
        """The firestore database."""
        return self.__db

    # user related methods
    def get_user(self, user_id: str) -> firestore.DocumentSnapshot:
        """Returns the user document with ID `user_id` if exists.
        
        Raises
        ------
        M2WDatabaseException: if user doesn't exist.
        """
        user_ref = self.__db.collection('users').document(user_id)
        user = user_ref.get()
        if user.exists:
            return user
        else:
            raise M2WDatabaseException("User does not exist.")
        
    def get_user_ref(self, user_id: str) -> firestore.DocumentReference:
        """Returns the reference to a user with ID `user_id` 
        if the user exists.
        
        Raises
        ------
        M2WDatabaseException: if user doesn't exist.
        """
        user_ref = self.__db.collection('users').document(user_id)
        user = user_ref.get()
        if user.exists:
            return user_ref
        else:
            raise M2WDatabaseException("User does not exist.")
        
    def get_user_blocklist(self, user_id: str) -> firestore.CollectionReference:
        """Returns the reference to the blocklist collection of a user 
        with ID `user_id` if the user exists.
        
        Raises
        ------
        M2WDatabaseException: if user doesn't exist.
        """
        user_ref = self.__db.collection('users').document(user_id)
        user = user_ref.get()
        if user.exists:
            return user_ref.collection('blocklist')
        else:
            raise M2WDatabaseException("User does not exist.")
        
    def set_user_data(self, user_id: str, data: dict, merge: bool=True):
        """Creates or updates a user.
        
        Parameters
        ----------
        user_id: the ID of the user in the database.
        data: a dictionary containing the data fields of the user.
        merge: if `True` updates the provided fields of the existing user, 
        if `False` overwrites the existing user with the only the new content. 
        Creates the user if it doesn't exist in both cases.
        """
        return self.__db.collection("users").document(user_id).set(document_data=data, merge=merge)
        
    def get_all_users(self) -> Generator[firestore.DocumentSnapshot]:
        """Return a stream containing all users."""
        return self.__db.collection("users").stream()
    
    # movie related methods
    def get_movie(self, movie_id: str) -> firestore.DocumentSnapshot:
        """Returns the movie document with ID `movie_id` if exists.
        
        Raises
        ------
        M2WDatabaseException: if the movie doesn't exist.
        """
        movie_ref = self.__db.collection('movies').document(movie_id)
        movie = movie_ref.get()
        if movie.exists:
            return movie
        else:
            raise M2WDatabaseException("User does not exist.")
    
    def remove_movie_from_blocklist(self, user_id: str, movie_id: str) -> bool:
        """Removes the movie from the blocklist of the user.
        
        Parameters
        ----------
        user_id: ID of the memeber in m2w users
        movie_id: ID of the movie in TMDB

        Returns
        -------
        True if successfull, False otherwise.
        """
        try:
            block_ref = self.get_user_blocklist(user_id=user_id)
            mov_ref = block_ref.document(movie_id).get()
            if mov_ref.exists:
                block_ref.document(movie_id).delete()
        except:
            return False
        else:
            return True
    
    def add_to_blocklist(self, user_id: str, movie_id: str, movie_title: Optional[str] = None) -> bool:
        """Adds a movie to the blocklist of the member.
        
        Parameters
        ----------
        user_id: ID of the memeber in m2w users
        movie_id: ID of the movie in TMDB
        movie_title: the title of the movie in TMDB

        Returns
        -------
        True if successfull, False otherwise.
        """
        if movie_title is None:
            try:
                movie_data = self.get_movie(movie_id=movie_id).to_dict()
                movie_title = movie_data['title']
            except:
                pass
        data = {"title":movie_title}
        try:
            self.get_user_blocklist(user_id=user_id).document(movie_id).set(data)
        except:
            return False
        else:
            return True
