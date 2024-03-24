from typing import Optional
from src.authenticate import Account
from src.movies import Movie
# from authenticate import Account
# from movies import Movie
from google.cloud.firestore import Client as fsClient


class fsWatchGroup():
    """Bundles the watchgroup specific methods."""

    def __init__(
            self,
            id: str,
            database: fsClient,
            tmdb_token: str,
            name: Optional[str] = None,
            locale: Optional[str] = None,
            members: Optional[list] = None,
            primary_member: Optional[str] = None
            ) -> None:
        """Represents a watch group.
        
        Parameters
        ----------
        id: the ID of the group in the m2w database
        database: the firestore client for the m2w database
        tmdb_token: the TMDB bearer token
        name: the name of the group
        locale: the locale code of the group
        members: the list of the group members as Accounts.
        primary_member: the member currently logged on. 
        If omitted uses the first member on the list.
        
        """
        self.id = id
        self.db = database
        self.__tmdb_token = tmdb_token
        self.primary_member = primary_member
        if (name and locale and members) is not None:
            self.name = name
            self.locale = locale
            self.members = members
        else:
            self.get_data()
    
    def get_data(self) -> None:
        """Gets the groups content and sets the parameters."""
        group_ref = self.db.collection("groups").document(self.id)
        data = group_ref.get().to_dict()
        self.name = data["name"]
        self.locale = data["locale"]
        members = group_ref.collection("members").stream()
        self.members = []
        for member in members:
            user_ref = self.db.collection("users").document(member.id)
            user_data = user_ref.get().to_dict()
            user_acc = Account(
                token=self.__tmdb_token,
                session_id=user_data["tmdb_session"],
                blocklist=self.get_user_blocklist(member=member.id),
                m2w_id=member.id,
                m2w_nick=user_data["nickname"],
                m2w_email=user_data["email"],
                **user_data["tmdb_user"]
            )
            self.members.append(user_acc)
            if self.primary_member is None:
                self.primary_member = member.id

    def get_user_blocklist(self, member: str) -> list[int]:
        """Return the blocklist of a user."""
        blocklist = self.db.collection("users").document(member).collection("blocklist").stream()
        result = []
        for blocked in blocklist:
            result.append(int(blocked.id))
        return result
    
    def get_member(self, m2w_id: str) -> Account:
        """Returns the member with the m2w_id."""
        for member in self.members:
            if member.m2w_id == m2w_id:
                return member
        else:
            return None
    
    def remove_from_blocklist(self, member: str, movie_id: str) -> None:
        """Removes the movie from the blocklist of the member.
        
        Parameters
        ----------
        member: ID of the memeber in m2w users
        movie_id: ID of the movie in TMDB

        Returns
        -------
        True if successfull, False otherwise.
        """
        movie_id = str(movie_id)
        try:
            user_ref = self.db.collection("users").document(member)
            user_ref.collection("blocklist").document(movie_id).delete()
        except:
            return False
        else:
            return True
        
    def add_to_blocklist(self, member: str, movie_id: str, movie_title: str) -> None:
        """Adds a movie to the blocklist of the member.
        
        Parameters
        ----------
        member: ID of the memeber in m2w users
        movie_id: ID of the movie in TMDB
        movie_title: the title of the movie in TMDB

        Returns
        -------
        True if successfull, False otherwise.
        """
        movie_id = str(movie_id)
        data = {"title":movie_title}
        try:
            user_ref = self.db.collection("users").document(member)
            user_ref.collection("blocklist").document(movie_id).set(data)
        except:
            return False
        else:
            return True

    def get_movie_grouplist_union(self) -> list:
        """ Gather the watchlist from every member.
        
        Build a list based on the union of all lists. 
        
        Returns
        -------
            A list with every movie.
        """
        movies = {}
        votes = {}
        for member in self.members:
            watchlist = member.get_watchlist_movie()
            for mov in watchlist:
                if votes.get(mov['id'], False):
                    votes[mov['id']][member.m2w_id] = "liked"
                else:
                    votes[mov['id']] = {}
                    votes[mov['id']][member.m2w_id] = "liked"
                movies[mov['id']] = mov
                if mov['id'] in member.blocklist:
                    self.remove_from_blocklist(
                        member=member.m2w_id,
                        movie_id=mov['id']
                    )
                    member.blocklist.remove(mov['id'])
            for mov in member.blocklist:
                if votes.get(mov, False):
                    votes[mov][member.m2w_id] = "blocked"
                else:
                    votes[mov] = {}
                    votes[mov][member.m2w_id] = "blocked"
        result = []
        for mov in movies.values():
            vote = {}
            for member in self.members:
                vote[member.m2w_id] = votes[mov['id']].get(member.m2w_id, "none")
            mov["votes"] = vote
            result.append(mov)
        return result


# if __name__ == "__main__":
#     from authenticate import SecretManager
#     from google.oauth2 import service_account

#     secrets = SecretManager()
#     db_cert = service_account.Credentials.from_service_account_file(secrets.firestore_cert)
#     db = fsClient(project=secrets.firestore_project, credentials=db_cert)

#     my_group = fsWatchGroup(
#         id="cf1lfA0B9k919oMaurS0",
#         database=db,
#         tmdb_token=secrets.tmdb_token
#     )
#     print(my_group.get_movie_grouplist_union())
#     my_group.members[0].add_movie_to_watchlist(movie_id=550)
#     print(my_group.get_movie_grouplist_union())
#     my_group.members[0].remove_movie_from_watchlist(movie_id=550)
#     print(my_group.get_movie_grouplist_union())