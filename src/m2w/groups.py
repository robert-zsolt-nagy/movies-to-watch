from typing import Optional
from ..tmdb.authenticate import Account
from ..tmdb.movies import Movie

class watch_group():
    """ Methods related to a watch group of users."""

    def __init__(
            self,
            memebers: Optional[list[Account]]=None,
            ) -> None:
        """ A group of users who want to watch movies together. 
        
        Parameters
        ----------
            members: a list of Account objects that represents the members

        """
        self.__members = memebers

    @property
    def members(self) -> list[Account]:
        return self.__members
    
    @members.setter
    def set_members(self, value):
        self.__members = value

    def get_grouplist_union(self) -> list:
        """ Gather the watchlist from every member.
        
        Build a list based on the union of all lists. 
        
        Returns
        -------
            A list with every movie.
        """
        movies = {}
        for member in self.members:
            watchlist = member.get_watchlist_movie()
            for mov in watchlist:
                movies[mov['id']] = mov
        result = []
        for mov in movies.values():
            result.append(mov)
        return result
