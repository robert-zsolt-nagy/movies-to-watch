from google.cloud import firestore
from google.oauth2 import service_account
from typing import Generator, Optional, Union

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
        self.user = M2wUserHandler(db=self.database)
        self.movie = M2wMovieHandler(db=self.database)
        self.group = M2wGroupHandler(db=self.database)

    @property
    def database(self) -> firestore.Client:
        """The firestore database."""
        return self.__db

class M2wDocumentHandler():
    """An item in the movies-to-watch database."""
    def __init__(
            self, 
            db: firestore.Client,
            collection: str,
            kind: str="Document"
            ) -> None:
        """Returns a represantation of a document.

        Parameters
        ----------
        db: the client for the firestore API.
        collection: the ID of the collection that contains the document.
        """
        self.__db = db
        self.__collection = collection
        self.__kind = kind

    def get_one(self, id_: str) -> firestore.DocumentSnapshot:
        """Returns a document with ID `id_` if exists.
        
        Raises
        ------
        M2WDatabaseException: if document doesn't exist.
        """
        doc_ref = self.__db.collection(self.__collection).document(id_)
        doc = doc_ref.get()
        if doc.exists:
            return doc
        else:
            raise M2WDatabaseException(f"{self.__kind} does not exist.")
        
    def get_all(self) -> Generator[firestore.DocumentSnapshot]:
        """Returns a stream with all documents in the collection.
        
        Raises
        ------
        M2WDatabaseException: if document doesn't exist.
        """
        return self.__db.collection(self.__collection).stream()
    
    def set_data(self, id_: str, data: dict, merge: bool=True):
        """Creates or updates a document.
        
        Parameters
        ----------
        id_: the ID of the document in the database.
        data: a dictionary containing the data fields of the document.
        merge: if `True` updates the provided fields of the existing document, 
        if `False` overwrites the existing document with the only the new content. 
        Creates the document if it doesn't exist in both cases.
        """
        return self.__db.collection(self.__collection).document(id_).set(document_data=data, merge=merge)
    
    def delete(self, id_: str) -> bool:
        """Deletes a document. 
        
        Parameters
        ----------
        id_: the ID of the document in the database.

        Returns
        -------
        True is successfully deleted, False otherwise.
        """
        try:
            self.__db.collection(self.__collection).document(id_).delete()
        except:
            return False
        else:
            return True


class M2wUserHandler(M2wDocumentHandler):
    def __init__(self, db: firestore.Client) -> None:
        super().__init__(db, collection='users', kind='User')

    def get_blocklist(self, user_id: str) -> firestore.CollectionReference:
        """Returns the reference to the blocklist collection of a user 
        with ID `user_id` if the user exists.
        
        Raises
        ------
        M2WDatabaseException: if user doesn't exist.
        """
        user_ref = self.__db.collection(self.__collection).document(user_id)
        user = user_ref.get()
        if user.exists:
            return user_ref.collection('blocklist')
        else:
            raise M2WDatabaseException(f"{self.__kind} does not exist.")
        
class M2wMovieHandler(M2wDocumentHandler):
    def __init__(self, db: firestore.Client) -> None:
        super().__init__(db, collection='movies', kind="Movie")

    def remove_from_blocklist(self, movie_id: str, blocklist: firestore.CollectionReference) -> bool:
        """Removes the movie from the blocklist.
        
        Parameters
        ----------
        movie_id: ID of the movie in TMDB.
        blocklist: the reference of the affected blocklist.

        Returns
        -------
        True if successfull, False otherwise.
        """
        try:
            blocklist.document(movie_id).delete()
        except:
            return False
        else:
            return True
        
    def add_to_blocklist(self, movie_id: str, blocklist: firestore.CollectionReference, movie_title: Optional[str] = None) -> bool:
        """Adds a movie to the blocklist of the member.
        
        Parameters
        ----------
        movie_id: ID of the movie in TMDB
        blocklist: the reference of the affected blocklist.
        movie_title: the title of the movie in TMDB

        Returns
        -------
        True if successfull, False otherwise.
        """
        if movie_title is None:
            try:
                movie_data = self.get_one(id_=movie_id).to_dict()
                movie_title = movie_data['title']
            except:
                movie_title = 'unknown'
        data = {"title":movie_title}
        try:
            blocklist.document(movie_id).set(data)
        except:
            return False
        else:
            return True

class M2wGroupHandler(M2wDocumentHandler):
    def __init__(self, db: firestore.Client) -> None:
        super().__init__(db, collection='groups', kind='Group')

    def get_all_group_members(self, group_id: str) -> Generator[firestore.DocumentSnapshot]:
        """Returns a stream with all member documents in the group.
        
        Parametes
        ---------
        group_id: the ID of the group in M2W Database.

        Raises
        ------
        M2WDatabaseException: if member document doesn't exist.
        """
        try:
            group_ref = self.get_one(id_=group_id).reference
        except:
            raise M2WDatabaseException(f"{self.__kind} does not exist.")
        else:
            return group_ref.collection('members').stream()
        
    def add_member_to_group(self, group_id: str, user: firestore.DocumentSnapshot) -> bool:
        """Adds a user to the members of the group.
        
        Parameters
        ----------
        group_id: the ID of the group.
        user: a Snapshot of the user document.

        Returns
        -------
        True if successfull, False otherwise.
        """
        try:
            group_ref = self.get_one(id_=group_id).reference
            group_ref.collection('members').document(user.id).set(user.to_dict())
        except:
            return False
        else:
            return True
        
    def remove_member_from_group(self, group_id: str, user_id: str) -> bool:
        """Adds a user to the members of the group.
        
        Parameters
        ----------
        group_id: the ID of the group.
        user_id: the M2W ID of the user.

        Returns
        -------
        True if successfull, False otherwise.
        """
        try:
            group_ref = self.get_one(id_=group_id).reference
            group_ref.collection('members').document(user_id).delete()
        except:
            return False
        else:
            return True
    
    def create_new(self, data: dict, members: Optional[Union[list[firestore.DocumentSnapshot], firestore.DocumentSnapshot]]=None) -> str:
        """Creates a new group.
        
        Parameters
        ----------
        data: the data fields of the group.
        memebers: a single member or a list of members for the group.
        
        Returns
        -------
        The ID for the created group

        Raises
        ------
        M2WDatabaseException: if the group couldn't be created.
        """
        try:
            _, group_ref = self.__db.collection("groups").add(document_data=data)
            if members is not None:
                if not isinstance(members, list):
                    members = [members]
                for member in members:
                    self.add_member_to_group(group_id=group_ref.id, user=member)
        except:
            raise M2WDatabaseException("Could not create group.")
        else:
            return group_ref
