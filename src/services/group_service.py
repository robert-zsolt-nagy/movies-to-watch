from src.dao.m2w_database import M2WDatabase
from src.dao.secret_manager import SecretManager
from src.services.user_service import UserManagerService
from src.services.movie_caching import MovieCachingService
from typing import Literal, Union
from collections.abc import Generator


class GroupManagerServiceException(Exception):
    """Base class for Exceptions related to the Group Manager Service."""

class InvalidVoteError(GroupManagerServiceException):
    """Vote parameter is not supported."""

class GroupManagerService():
    """Handles the Watchgroup administration and data retreival."""
    def __init__(
            self,
            secrets: SecretManager,
            m2w_db: M2WDatabase,
            user_service: UserManagerService,
            movie_service: MovieCachingService
            ) -> None:
        """Handles the Watchgroup administration and data retreival.
        
        Parameters
        ----------
        secrets: container of external secrets.
        m2w_db: bundle of firestore related methods for M2W.
        user_service: handles the user administration.
        movie_service: handles the movie caching and data retreival.
        """
        self._secrets = secrets
        self.group = m2w_db.group
        self.user = user_service
        self.movie = movie_service

    def _like_movie(self, user_id: str, movie_id: str) -> bool:
        """Indicate that user wants to watch movie.
        
        Parameters
        ----------
        user_id: the M2W ID of the user.
        movie_id: the M2W ID of the movie.

        Returns
        -------
        True if successful.

        Raises
        ------
        GroupManagerServiceException in case of error.
        """
        # add movie to watchlist
        watchlist_response = self.user.add_movie_to_users_watchlist(movie_id=movie_id, user_id=user_id)
        if watchlist_response:
            # remove movie from blocklist
            blocklist = self.user.get_blocklist(user_id=user_id)
            blocklist_response = self.movie.remove_movie_from_blocklist(movie_id=movie_id, blocklist=blocklist)
            if blocklist_response:
                return True
            else:
                GroupManagerServiceException("Remove from blocklist failed.")
        else:
            raise GroupManagerServiceException("Add to watchlist failed.")
        
    def _block_movie(self, user_id: str, movie_id: str):
        """Indicate that user does not want to watch movie.
        
        Parameters
        ----------
        user_id: the M2W ID of the user.
        movie_id: the M2W ID of the movie.

        Returns
        -------
        True if successful.

        Raises
        ------
        GroupManagerServiceException in case of error.
        """
        # add movie to watchlist
        watchlist_response = self.user.remove_movie_from_users_watchlist(movie_id=movie_id, user_id=user_id)
        if watchlist_response:
            # remove movie from blocklist
            blocklist = self.user.get_blocklist(user_id=user_id)
            blocklist_response = self.movie.add_movie_to_blocklist(movie_id=movie_id, blocklist=blocklist)
            if blocklist_response:
                return True
            else:
                GroupManagerServiceException("Add to blocklist failed.")
        else:
            raise GroupManagerServiceException("Remove from watchlist failed.")
        
    def vote_for_movie_by_user(self, movie_id: str, user_id: str, vote: Literal["like", "block"]) -> bool:
        """Cast a vote in the name of a user for a movie.
        
        Parameters
        ----------
        movie_id: str, 
        user_id: str, 
        vote:

        Returns
        -------
        True if successful.

        Raises
        ------
        GroupManagerServiceException in case of error.
        """
        if vote == "like":
            return self._like_movie(user_id=user_id, movie_id=movie_id)
        elif vote == "block":
            return self._block_movie(user_id=user_id, movie_id=movie_id)
        else:
            raise InvalidVoteError(f"Vote parameter '{vote}' is unsupported.")
        
    def watch_movie_by_user(self, movie_id: Union[int, str], user_id: str) -> bool:
        """Watch a movie alone.
        
        Parameters
        ----------
        movie_id: the ID of the movie.
        user_id: the M2W ID of the user.

        Returns
        -------
        True if successful, False otherwise.
        """
        try:
            self.vote_for_movie_by_user(movie_id=str(movie_id), user_id=user_id, vote='block')
        except Exception as e:
            raise GroupManagerServiceException(e)
        else:
            return True
        
    def watch_movie_by_group(self, movie_id: Union[int, str], group_id: str):
        """Watch a movie with a group together.
        
        Parameters
        ----------
        movie_id: the ID of the movie.
        group_id: the M2W ID of the group. 

        Returns
        -------
        True if successful, False otherwise.
        """
        try:
            users = self.get_all_members(group_id=group_id)
            for user in users:
                self.watch_movie_by_user(movie_id=movie_id, user_id=user.id)
        except Exception as e:
            raise GroupManagerServiceException(e)
        else:
            return True
        
    def get_watchgroup_data(self, group_id: str) -> dict:
        """Get the datasheet of the watchgroup.
        
        Parameters
        ----------
        group_id: the M2W ID of the group.
        """
        group = self.group.get_one(id_=group_id)
        group_data = group.to_dict()
        return group_data
    
    def get_all_members(self, group_id: str):
        """Get all members of the watchgroup.
        
        Parametes
        ---------
        group_id: the ID of the group in M2W Database.

        Raises
        ------
        M2WDatabaseException: if group doesn't exist.
        """
        return self.group.get_all_group_members(group_id=group_id)
    
    def get_combined_watchlist_of_members(self, users: Generator):
        """Get the watchlist of all members and consolidate them in a single list.
        
        Parameters
        ----------
        users: a generator of all relevant users.

        Returns
        -------
        The consolidated data as a single list.

        Raises
        ------
        WatchlistCreationError if any error occures.
        """
        return self.movie.get_combined_watchlist_of_users(users=users)

    def get_group_votes(self, group_id: str) -> dict:
        """Get the raw content of the group with votes.
        
        Parametes
        ---------
        group_id: the ID of the group in M2W Database.

        Returns
        -------
        The dictionary of all cast votes.

        Raises
        ------
        GroupManagerServiceException in case of error.
        """
        try:
            # get all members
            all_members = self.get_all_members(group_id=group_id)
            # collect lists
            vote_map = {}
            for member in all_members:
                # get watchlist
                watchlist = self.user.get_movies_watchlist(user_id=member.id)
                # get blocklist
                blocklist_ref = self.user.get_blocklist(user_id=member.id)
                # register votes
                for movie in watchlist:
                    # register "liked" if on watchlist
                    if vote_map.get(movie['id'], False):
                        vote_map[movie['id']][member.id] = "liked"
                    else:
                        vote_map[movie['id']] = {}
                        vote_map[movie['id']][member.id] = "liked"
                    # remove from user's blocklist if on user's watchlist
                    for blocked_movie in blocklist_ref.stream():
                        if int(blocked_movie.id) == movie['id']:
                            self.movie.remove_movie_from_blocklist(
                                movie_id=str(movie['id']),
                                blocklist=blocklist_ref
                                )
                            break
                for blocked_movie in blocklist_ref.stream():
                    # register "blocked" if on blocklist
                    _id = int(blocked_movie.id)
                    if vote_map.get(_id, False):
                        vote_map[_id][member.id] = "blocked"
                    else:
                        vote_map[_id] = {}
                        vote_map[_id][member.id] = "blocked"
        except Exception:
            raise GroupManagerServiceException('Error during vote collection.')
        else:
            return vote_map
        
    def get_raw_group_content_from_votes(self, votes: dict) -> dict:
        """Gets the group content from votes.
        
        Paramters
        ---------
        votes: the dictionary of the cast votes per movie.

        Returns
        -------
        The raw content of the group without the movies with 
        only "blocked" votes.

        Raises
        ------
        GroupManagerServiceException in case of error.
        """
        try:
            group_content = {}
            for movie_id, vote in votes.items():
                tally = [user_vote for user_vote in vote.values()]
                if "liked" in tally:
                    details = self.movie.get_movie_details(movie_id=movie_id)
                    group_content[movie_id] = details
                    group_content[movie_id]['votes'] = vote
        except Exception as e:
            raise GroupManagerServiceException(e)
        else:
            return group_content
        
    def get_group_content(self, group_id: str, primary_user: str) -> list[dict]:
        """Get the group content prepared for the relevant page.
        
        Parameters
        ----------
        group_id: the M2W ID of the group.
        primary_user: the M2W ID of the primary user.
        
        Returns
        -------
        The content of the group as sorted list of movie dictionaries. 
        """
        try:
            watchlist = []
            votes = self.get_group_votes(group_id=group_id)
            raw_content = self.get_raw_group_content_from_votes(votes=votes)
            for _, details in raw_content.items():
                datasheet = {
                    'id': details['id'],
                    'title': details['title'],
                    'poster_path': None,
                    'release_date': details['release_date'],
                    'genres': None,
                    'runtime': details['runtime'],
                    'overview': details['overview'],
                    'official_trailer': details['official_trailer'],
                    'tmdb': None,
                    'providers': None,
                    'votes': None
                }
                # convert poster path
                poster_path = f"{self._secrets.tmdb_image}/t/p/original{details['poster_path']}"
                datasheet['poster_path'] = poster_path
                # convert genres
                datasheet['genres'] = self.convert_genres(details['genres'])
                # fill tmdb
                tmdb = f"{self._secrets.tmdb_home}/movie/{details['id']}"
                datasheet['tmdb'] = tmdb
                # process providers
                datasheet['providers'] = self.process_providers(providers=details['local_providers'], group_id=group_id)
                # process votes
                datasheet['votes'] = self.process_votes(votes=details['votes'], primary_user=primary_user)
                watchlist.append(datasheet)
            # sort watchlist
            watchlist = self.default_sort_watchlist(watchlist=watchlist)
        except Exception as e:
            raise GroupManagerServiceException(e)
        else:
            return watchlist
        
    @staticmethod
    def default_sort_watchlist(watchlist: list) -> list:
        """Sorts the watchlist and returns the result."""
        # sort by title ascending
        def by_title(value):
            return value['title']
        watchlist.sort(key=by_title)
        # sort by vote count descending
        def by_vote_count(value):
            votes = value['votes']
            result = len(votes['liked'])
            return result
        watchlist.sort(key=by_vote_count, reverse=True)
        # sort by provider availability descending
        def by_provider(value):
            stream = value['providers']['stream']
            buy_or_rent = value['providers']['buy_or_rent']
            score = 0
            if len(stream) > 0:
                score += 2
            if len(buy_or_rent) > 0:
                score += 1
            return score
        watchlist.sort(key=by_provider, reverse=True)
        # sort by primary users vote descending
        def by_my_vote(value):
            if value['votes']['primary_vote'] is None:
                score = 2
            elif value['votes']['primary_vote'] == 'liked':
                score = 1
            else:
                score = 0
            return score
        watchlist.sort(key=by_my_vote, reverse=True)
        return watchlist

    @staticmethod
    def convert_genres(genres: list) -> str:
        """Converts genres to datasheet format.
        
        Parameters
        ----------
        genres: the list of the genre data.

        Returns
        -------
        The genre names converted to a comma separated string.
        """
        try:
            temp = []
            for genre in genres:
                temp.append(genre["name"])
            result = ", ".join(temp)
        except Exception:
            return "..."
        else:
            return result
        
    def process_providers(self, providers: dict, group_id: str) -> dict:
        """Filter and consolidate the providers to datasheet format.
        
        Parameters
        ----------
        providers: the dict of the provider data.
        group_id: the ID of the group in M2W Database.

        Returns
        -------
        The data filtered only for the locale relevant provider 
        and the buy and rent optiones merged to a single category. 
        ```
        {
            "stream":[],
            "buy_or_rent":[]
        }
        ```
        """
        datasheet = {
            "stream":[],
            "buy_or_rent":[]
        }
        try:
            group_data = self.get_watchgroup_data(group_id=group_id)
            locale = group_data.get("locale", "HU")
            local_providers = providers.get(locale, False)
            if local_providers:
                # collect stream
                stream = local_providers.get("flatrate", False)
                if stream:
                    datasheet['stream'] = self.convert_provider_logo_path(stream)
                # compile buy and rent
                buy_or_rent = {}
                buy = local_providers.get('buy', False)
                if buy:
                    for current in buy:
                        buy_or_rent[current["provider_id"]] = current
                rent = local_providers.get('rent', False)
                if rent:
                    for current in rent:
                        buy_or_rent[current["provider_id"]] = current
                if buy_or_rent:
                    temp = [prov for prov in buy_or_rent.values()]
                    datasheet['buy_or_rent'] = self.convert_provider_logo_path(temp)
        except Exception:
            return {
                "stream":[],
                "buy_or_rent":[]
            }
        else:
            return datasheet
        
    def convert_provider_logo_path(self, providers: list[dict]) -> list[dict]:
        """Adds the URL to the logo path of each provider."""
        for provider in providers:
            logo_path = provider.get("logo_path", False)
            if logo_path:
                provider['logo_path'] = f"{self._secrets.tmdb_image}/t/p/original{logo_path}"
            else:
                provider['logo_path'] = ""
        return providers
        
    def process_votes(self, votes: dict, primary_user: str) -> dict:
        """Prepares the votes in datasheet format.
        
        Parameters
        ----------
        votes: the vote map of the movie.
        primary_user: the ID of the primary user in M2W Database.

        Returns
        -------
        A dictionary with the primary vote and all other votes.
        ```
        {
            "primary_vote":str,
            "liked":[],
            "blocked":[]
        }
        ```
        """
        datasheet = {
            "primary_vote": None,
            "liked": [],
            "blocked": []
        }
        try:
            for user, vote in votes.items():
                if user == primary_user:
                    datasheet['primary_vote'] = vote
                else:
                    user_data = self.user.get_m2w_user_profile_data(user_id=user)
                    temp = {
                        'nickname':user_data.get('nickname', ""),
                        'email':user_data.get('email', ""),
                        'profile_pic': user_data.get('profile_pic', "01.png")
                    }
                    datasheet[vote].append(temp)
        except Exception:
            return {
                "primary_vote": None,
                "liked": [],
                "blocked": []
            }
        else:
            return datasheet
        
        