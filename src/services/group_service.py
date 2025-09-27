from uuid import UUID

from neo4j import Driver, Transaction

from src.dao.m2w_graph_db_entities import M2WDatabaseException, Availability, ProviderFilter
from src.dao.m2w_graph_db_repository_availabilities import get_all_availabilities_for_movies
from src.dao.m2w_graph_db_repository_movies import get_all_movies_for_watchlist
from src.dao.m2w_graph_db_repository_votes_and_watch_status import vote_for_movie, mark_movie_as_watched, \
    get_all_votes_of_watchlist, get_all_watch_history_of_watchlist
from src.dao.m2w_graph_db_repository_watchlists import get_watchlist_details, get_primary_watchlist_id
from src.dao.secret_manager import SecretManager
from src.services.m2w_dtos import VoteValueDto, MovieDto, ProviderDto, WatchListDto
from src.services.user_service import UserManagerService


class GroupManagerServiceException(Exception):
    """Base class for Exceptions related to the Group Manager Service."""


class InvalidVoteError(GroupManagerServiceException):
    """Vote parameter is not supported."""


class GroupManagerService:
    """Handles the watch group administration and data retrieval."""

    def __init__(
            self,
            secrets: SecretManager,
            db: Driver,
            user_service: UserManagerService
    ) -> None:
        """Handles the watch group administration and data retrieval.
        
        Parameters
        ----------
        secrets:
            container of external secrets.
        db:
            the Neo4j driver to use for the database operations
        user_service:
            handles the user data retrieval.
        """
        self._secrets = secrets
        self.db = db
        self.user = user_service

    def vote_for_movie_by_user(self, user_id: str, movie_id: int, vote: VoteValueDto) -> bool:
        """Cast a vote in the name of a user for a movie.
        
        Parameters
        ----------
        user_id:
            the M2W ID of the user.
        movie_id:
            the M2W ID of the movie.
        vote:
            The vote to cast. Either "like" or "block".

        Returns
        -------
        bool
            True if successful.

        Raises
        ------
        GroupManagerServiceException
            in case of error.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            vote_for_movie(tx, user_id, movie_id, vote.to_entity())

            if vote == VoteValueDto.YEAH:
                watchlist_response = self.user.add_movie_to_users_watchlist(movie_id=movie_id, user_id=user_id)
            else:
                watchlist_response = self.user.remove_movie_from_users_watchlist(movie_id=movie_id, user_id=user_id)

            if not watchlist_response:
                if vote == VoteValueDto.YEAH:
                    raise GroupManagerServiceException("Add to TMDB watchlist failed.")
                else:
                    raise GroupManagerServiceException("Remove from TMDB watchlist failed.")
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise GroupManagerServiceException(e)
        else:
            tx.commit()
            return True
        finally:
            if session is not None:
                session.close()

    def watch_movie_by_user(self, user_id: str, movie_id: int) -> bool:
        """Watch a movie alone.
        
        Parameters
        ----------
        user_id:
            the M2W ID of the user.
        movie_id:
            the ID of the movie.

        Returns
        -------
        bool
            True if successful, False otherwise.

        Raises
        ------
        GroupManagerServiceException
            in case of error.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            result = self._watch_movie(tx, movie_id, user_id)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise GroupManagerServiceException(e)
        else:
            tx.commit()
            return result
        finally:
            if session is not None:
                session.close()

    def watch_movie_by_group(self, group_id: UUID, user_id: str, movie_id: int):
        """Watch a movie with a group together.

        Parameters
        ----------
        group_id: UUID
            the M2W ID of the group.
        movie_id: int
            the ID of the movie.
        user_id: str
            the current user performing the action.

        Returns
        -------
        bool
            True if successful, False otherwise.

        Raises
        ------
        GroupManagerServiceException
            in case of error.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            users = get_watchlist_details(tx, watchlist_id=group_id).users
            result = True
            is_member = False
            for u in users:
                if u.user_id == user_id:
                    is_member = True
            if not is_member:
                raise GroupManagerServiceException("User is not a member of the group.")
            for user in users:
                result = result & self._watch_movie(tx=tx, movie_id=movie_id, user_id=user.user_id)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise GroupManagerServiceException(e)
        else:
            tx.commit()
            return result
        finally:
            if session is not None:
                session.close()

    def get_primary_group_for_m2w_user(self, user_id: str) -> WatchListDto:
        """
        Get the details of the primary group for the user.

        Parameters
        ----------
        user_id: str
            the M2W ID of the user.

        Returns
        -------
        WatchListDto
            the primary group for the user.

        Raises
        ------
        UserManagerException
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            group_id = get_primary_watchlist_id(tx=tx, user_id=user_id)
            watchlist = get_watchlist_details(tx=tx, watchlist_id=group_id)
            result = WatchListDto.from_entity(watchlist)
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise GroupManagerServiceException(f"Failed to get primary group: {e}")
        else:
            tx.commit()
            return result
        finally:
            if session is not None:
                session.close()

    # TODO: test me
    def get_group_content(self, group_id: UUID, current_user_id: str) -> list[MovieDto]:
        """Get the content of the group with votes and availability included.

        Parameters
        ----------
        group_id:
            the ID of the group in M2W Database.
        current_user_id:
            the ID of the current user browsing the group.

        Returns
        -------
        list[MovieDto]:
            The list of all movies in the group.

        Raises
        ------
        GroupManagerServiceException
            in case of error.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            watchlist = get_watchlist_details(tx=tx, watchlist_id=group_id)
            user_ids = []
            for member in watchlist.users:
                user_ids.append(member.user_id)
            movies = get_all_movies_for_watchlist(tx=tx, watchlist_id=watchlist.watchlist_id)
            movie_ids = []
            for movie in movies:
                movie_ids.append(movie.movie_id)
                movie.poster_path = self._convert_movie_poster_path(poster_path=movie.poster_path)
            votes = get_all_votes_of_watchlist(tx=tx, user_ids=user_ids, movie_ids=movie_ids)
            availabilities = get_all_availabilities_for_movies(
                tx=tx, movie_ids=movie_ids, provider_filters=watchlist.provider_filters)
            watch_history = get_all_watch_history_of_watchlist(tx=tx, user_ids=user_ids, movie_ids=movie_ids)
            # fix logo paths
            for a in availabilities:
                a.provider = self._convert_provider_logo_path(a.provider)

            movie_dtos = []
            for movie in movies:
                relevant_availabilities = []
                for availability in availabilities:
                    if availability.movie_id == movie.movie_id:
                        relevant_availabilities.append(availability)
                relevant_availabilities = self._keep_one_availability_per_provider(
                    availabilities=relevant_availabilities, provider_filters=watchlist.provider_filters)
                relevant_votes = []
                for vote in votes:
                    if vote.movie_id == movie.movie_id:
                        relevant_votes.append(vote)
                relevant_watches = []
                for watch in watch_history:
                    if watch.movie_id == movie.movie_id:
                        relevant_watches.append(watch)
                movie_dtos.append(MovieDto.from_entity(
                    movie=movie,
                    availabilities=relevant_availabilities,
                    votes=relevant_votes,
                    users=watchlist.users,
                    watch_history=relevant_watches,
                    current_user_id=current_user_id
                ))
            movie_dtos = self.default_sort_watchlist(movie_dtos)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise GroupManagerServiceException(f"Error during group content collection: {e}")
        else:
            tx.commit()
            return movie_dtos
        finally:
            if session is not None:
                session.close()

    @staticmethod
    def default_sort_watchlist(watchlist: list[MovieDto]) -> list[MovieDto]:
        """Sorts the watchlist and returns the result."""

        # sort by title ascending
        def by_title(value):
            return value.title

        watchlist.sort(key=by_title)

        # sort by vote count descending
        def by_vote_count(value):
            votes = value.votes
            result = len(votes['liked'])
            return result

        watchlist.sort(key=by_vote_count, reverse=True)

        # sort by provider availability descending
        def by_provider(value):
            stream = value.providers['stream']
            buy_or_rent = value.providers['buy_or_rent']
            score = 0
            if len(stream) > 0:
                score = 2
            elif len(buy_or_rent) > 0:
                score = 1
            return score

        watchlist.sort(key=by_provider, reverse=True)

        # sort by primary users vote descending
        def by_my_vote(value):
            if value.watched is True:
                score = 1
            elif value.votes['primary_vote'] is None:
                score = 3
            elif value.votes['primary_vote'] == 'liked':
                score = 2
            else:
                score = 0
            return score

        watchlist.sort(key=by_my_vote, reverse=True)
        return watchlist

    def _convert_provider_logo_path(self, provider: ProviderDto) -> ProviderDto:
        """Adds the URL to the logo path of each provider.

        Parameters
        ----------
        provider:
            the provider to convert.

        Returns
        -------
        ProviderDto
            The provider with the updated logo paths with the URL added.
        """
        logo_path = provider.logo_path
        if logo_path is not None and logo_path != "":
            provider.logo_path = f"{self._secrets.tmdb_image}/t/p/original{logo_path}"
        else:
            provider.logo_path = ""
        return provider

    def _convert_movie_poster_path(self, poster_path: str) -> str:
        """Adds the URL to the poster path.

        Parameters
        ----------
        poster_path:
            the poster path to convert.

        Returns
        -------
        str
            The updated poster path with the URL added.
        """
        if poster_path is not None and poster_path != "":
            return f"{self._secrets.tmdb_image}/t/p/original{poster_path}"
        else:
            return ""

    def _watch_movie(self, tx: Transaction, movie_id: int, user_id: str) -> bool:
        mark_movie_as_watched(tx=tx, user_id=user_id, movie_id=movie_id)
        watchlist_response = self.user.remove_movie_from_users_watchlist(movie_id=movie_id, user_id=user_id)
        if watchlist_response:
            return True
        else:
            raise GroupManagerServiceException("Remove from TMDB watchlist failed.")

    @staticmethod
    def _keep_one_availability_per_provider(
            availabilities: list[Availability], provider_filters: list[ProviderFilter]) -> list[Availability]:
        filters_by_provider_per_locale = {}
        for f in provider_filters:
            if f.provider_id not in filters_by_provider_per_locale:
                filters_by_provider_per_locale[f.provider_id] = {}
            filters_by_provider_per_locale[f.provider_id][f.location] = f.priority

        availabilities_per_provider = {}
        for availability in availabilities:
            if availability.provider.provider_id not in availabilities_per_provider:
                availabilities_per_provider[availability.provider.provider_id] = []
            availabilities_per_provider[availability.provider.provider_id].append(availability)
        filtered_availabilities = []
        for provider_id in availabilities_per_provider:
            selected_availability = None
            selected_priority = 2048000
            for a in availabilities_per_provider[provider_id]:
                prio = filters_by_provider_per_locale[provider_id][a.location]
                if prio < selected_priority:
                    selected_availability = a
                    selected_priority = prio
            filtered_availabilities.append(selected_availability)
        return filtered_availabilities