import logging
from datetime import datetime

from neo4j import Driver
from werkzeug.http import parse_age

from src.dao.m2w_graph_db_entities import VoteValue, Availability, Provider, AvailabilityType
from src.dao.m2w_graph_db_repository_availabilities import save_movie_availabilities
from src.dao.m2w_graph_db_repository_movies import get_one_movie_by_id, keep_movie_ids_where_update_is_needed, \
    save_or_update_movie, delete_details_of_obsolete_movies
from src.dao.m2w_graph_db_repository_users import count_tmdb_users, get_tmdb_users
from src.dao.m2w_graph_db_repository_votes_and_watch_status import vote_for_movie
from src.dao.m2w_graph_db_repository_watchlists import get_all_provider_filters
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.tmdb_movie_repository import TmdbMovieRepository
from src.dao.tmdb_user_repository import TmdbUserRepository
from src.services.m2w_dtos import MovieDto, GenreDto


class MovieNotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class MovieCacheUpdateError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class WatchlistCreationError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MovieCachingService:
    """Handles the movie caching and data retrieval."""
    def __init__(self, tmdb_http_client: TmdbHttpClient, db: Driver) -> None:
        """Handles the movie caching and data retrieval.
        
        Parameters
        ----------
        tmdb_http_client: TmdbHttpClient
            the client that handles the requests with the TMDB API.
        db: Driver
            The Neo4j driver.

        """
        self.user_repo = TmdbUserRepository(tmdb_http_client=tmdb_http_client)
        self.movie_repo = TmdbMovieRepository(tmdb_http_client=tmdb_http_client)
        self.db = db

    def get_movie_details_from_cache(self, movie_id: int) -> MovieDto:
        """Get the cached movie details from the M2W Database.
        
        Parameters
        ----------
        movie_id: int
            the TMDB ID of the movie as a string.

        Returns
        -------
        MovieDto
            The movie.

        Raises
        ------
        MovieNotFoundException
            if the movie does not exist.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            movie = get_one_movie_by_id(tx=tx, movie_id=movie_id)
            result = MovieDto.from_entity(movie=movie, availabilities=[], votes=[], users=[], watch_history=[])
        except Exception:
            if tx is not None:
                tx.rollback()
            raise MovieNotFoundException("Movie not cached.")
        else:
            tx.commit()
            return result
        finally:
            if session is not None:
                session.close()

    # TODO: test me
    def get_movie_details_from_tmdb(self, movie_id: int) -> MovieDto:
        """Get the movie details from the TMDB Database.
        
        Parameters
        ----------
        movie_id: int
            the TMDB ID of the movie as an integer.

        Returns
        -------
        MovieDto
            The result as a dictionary.

        Raises
        ------
        MovieNotFoundException
            if the movie does not exist.
        """
        try:
            response = self.movie_repo.get_details_by_id(movie_id=movie_id)
            release_date = datetime.strptime(response["release_date"], "%Y-%m-%d").date() \
                if (response["release_date"] is not None) and (response["release_date"] != "") \
                else None
            genres = []
            if  response["genres"] is not None:
                for genre in response["genres"]:
                    genres.append(GenreDto(genre_id=genre["id"], name=genre["name"]))
            official_trailer = self.movie_repo.get_trailer(movie_id=movie_id)
            movie = MovieDto(
                movie_id=response["id"],
                title=response["title"],
                overview=response["overview"],
                duration=response["runtime"],
                poster_path=response["poster_path"],
                genres=genres,
                official_trailer=official_trailer,
                original_language=response["original_language"],
                release_date=release_date,
                status=response["status"]
            )
        except Exception as e:
            raise MovieNotFoundException(f"Movie {movie_id} not found on TMDB. Error:{e}")
        else:
            return movie

    def get_movie_title(self, movie_id: int) -> str:
        """Get the movie details from M2W if cached or from TMDB if not cached.
        
        Parameters
        ----------
        movie_id: int
            the TMDB ID of the movie as an integer or string.

        Returns
        -------
        str
            The title of the movie

        Raises
        ------
        MovieNotFoundException
            if the movie does not exist.
        """
        return self.get_movie_details_from_cache(movie_id=movie_id).title

    # TODO: test me
    def movie_cache_update_job(self) -> bool:
        """
        Caches the details of every movie from every user's watchlist.
        
        Returns
        -------
        bool
            True if successful.
        
        Raises
        ------
        MovieCacheUpdateError
            in case of any error.
        """
        session = None
        tx = None
        movie_ids = set()
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            total = count_tmdb_users(tx=tx)
            logging.info(f"Processing data for {total} users.")
        except Exception:
            if tx is not None:
                tx.rollback()
            if session is not None:
                session.close()
            raise MovieCacheUpdateError("Error during update job.")
        else:
            if tx is not None:
                tx.commit()
            if session is not None:
                session.close()
            page_size = 20
            for offset in range(0, total, page_size):
                movie_ids = movie_ids.union(self._update_movie_cache_for_users(offset=offset, limit=page_size))
            self._update_movie_availabilities(movie_ids=movie_ids)
            self._remove_obsolete_movies()
            return True

    def _update_movie_cache_for_users(self, offset: int, limit: int):
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            users = get_tmdb_users(tx=tx, offset=offset, limit=limit)
        except Exception:
            if tx is not None:
                tx.rollback()
            if session is not None:
                session.close()
            raise MovieCacheUpdateError("Error during updating movie cache for users.")
        else:
            if tx is not None:
                tx.commit()
            if session is not None:
                session.close()
            movie_ids = set()
            logging.info(f"Processing batch for users {offset} - {offset + len(users)}.")
            for user in users:
                movie_ids = movie_ids.union(self._update_movie_cache_based_on_user_watchlist(user))
            return movie_ids

    def _update_movie_cache_based_on_user_watchlist(self, user) -> set[int]:
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            watchlist = self.user_repo.get_watchlist_movie(
                user_id=user.tmdb_id,
                session_id=user.session
            )
            movie_ids = []
            logging.info(f"Updating watchlist cache for {user.user_id}.")
            for movie in watchlist:
                movie_ids.append(movie['id'])
            update_needed_for_ids = keep_movie_ids_where_update_is_needed(tx=tx, movie_ids=movie_ids)
            logging.info(f"Update needed for {len(update_needed_for_ids)} movies out of {len(movie_ids)}.")
            # save the missing movies and update the outdated ones
            for movie_id in update_needed_for_ids:
                tmdb_movie = self.get_movie_details_from_tmdb(movie_id=movie_id)
                save_or_update_movie(tx=tx, movie=tmdb_movie.to_entity())
            # since the movie was on the user's watchlist, we can vote for it
            logging.info(f"Saving votes for {len(movie_ids)} movies of {user.user_id}.")
            for movie_id in movie_ids:
                vote_for_movie(tx=tx, user_id=user.user_id, movie_id=movie_id, vote_value=VoteValue.YEAH)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise MovieCacheUpdateError(f"Error during updating movie cache based on the {user.user_id} user's watchlist: {e}")
        else:
            tx.commit()
            return set(movie_ids)
        finally:
            if session is not None:
                session.close()

    def _remove_obsolete_movies(self):
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            logging.info("Removing obsolete movies.")
            delete_details_of_obsolete_movies(tx=tx)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise MovieCacheUpdateError(f"Error during deleting obsolete movies: {e}")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()

    def _update_movie_availabilities(self, movie_ids: set[int]):
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            logging.info(f"Updating availabilities for {len(movie_ids)} movies.")
            filters = get_all_provider_filters(tx=tx)
            filters_by_location = {}
            for f in filters:
                if f.location not in filters_by_location:
                    filters_by_location[f.location] = []
                filters_by_location[f.location].append(f.provider_id)
            for m in movie_ids:
                self._update_movie_availabilities_for_movie(movie_id=m, filters_by_location=filters_by_location)
        except Exception:
            if tx is not None:
                tx.rollback()
            raise MovieCacheUpdateError("Error during updating movie availability cache.")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()

    def _update_movie_availabilities_for_movie(self, movie_id: int, filters_by_location: dict[str, list[int]]):
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            availabilities = []
            watch_providers = self.movie_repo.get_watch_providers(movie_id=movie_id)
            for location_code in watch_providers.keys():
                included_providers = filters_by_location.get(location_code)
                if included_providers is None:
                    continue
                found_provider = watch_providers.get(location_code)
                if not isinstance(found_provider, dict):
                    continue
                for p_type in found_provider.keys():
                    if p_type not in ['free', 'ads', 'flatrate', 'rent', 'buy']:
                        continue
                    for p_at_location in found_provider.get(p_type):
                        p_id = p_at_location.get('provider_id')
                        if not p_id in included_providers:
                            continue
                        availabilities.append(Availability(
                            provider=Provider(
                                provider_id=p_id,
                                name=p_at_location.get('provider_name'),
                                logo_path=p_at_location.get('logo_path')
                            ),
                            movie_id=movie_id,
                            location=location_code,
                            watch_type=AvailabilityType(p_type)
                        ))
            save_movie_availabilities(tx=tx, movie_id=movie_id, availabilities=availabilities)
        except Exception:
            if tx is not None:
                tx.rollback()
            raise MovieCacheUpdateError(f"Error during updating movie availability cache for movie {movie_id}.")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()