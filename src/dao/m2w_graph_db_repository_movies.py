import logging
from datetime import datetime, timedelta, date
from uuid import UUID

from neo4j import Transaction

from src.dao.m2w_graph_db_entities import Movie, M2WDatabaseException, Genre


def get_all_genres_by_ids(tx: Transaction, genre_ids: list[int]) -> list[Genre]:
    """
    Finds all genres by their unique identifiers.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    genre_ids : list[int]
        The unique identifiers of the genres.

    Returns
    -------
    list[Genre]
        A list of genres.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    if (genre_ids is None) or (len(genre_ids) == 0):
        return []
    try:
        found_ids = tx.run(
            query="""
                MATCH (g:Genre)
                WHERE g.id IN $genre_ids
                RETURN g.id + "_" + g.name as name
            """,
            parameters={
                "genre_ids": genre_ids
            }
        ).fetch(len(genre_ids))
        genres = []
        for record in found_ids:
            genres.append(Genre.from_record(record["name"]))
        return genres
    except Exception as e:
        logging.error(f"Failed to find genres by id: {e}")
        raise M2WDatabaseException("Unable to find genres by id.")


def save_or_update_movie(tx: Transaction, movie: Movie):
    """
    Save or update a movie in the database. This function ensures that the movie
    information is either added as a new record or updated if it already
    exists.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    movie : Movie
        A Movie containing all attributes and details.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                    MERGE (m:Movie {id: $movie.id})
                    SET m = $movie
                """,
            parameters={
                "movie": {
                    "id": movie.movie_id,
                    "title": movie.title,
                    "overview": movie.overview,
                    "duration": movie.duration,
                    "poster_path": movie.poster_path,
                    "official_trailer": movie.official_trailer,
                    "original_language": movie.original_language,
                    "release_date": movie.release_date,
                    "status": movie.status,
                    "updated_at": movie.updated_at,
                }
            })
        tx.run(
            query="""
                    MATCH (:Genre)-[og:INCLUDES]->(:Movie {id: $movie_id})
                    DELETE og
                """,
            parameters={
                "movie_id": movie.movie_id
            })
        genres = []
        for genre in movie.genres:
            genres.append({
                "id": genre.genre_id,
                "name": genre.name
            })
        tx.run(
            query="""
                MATCH (m:Movie {id: $movie_id})
                WITH m
                UNWIND $genres AS genre
                MERGE (g:Genre {id: genre.id, name: genre.name})
                WITH m, g
                MERGE (g)-[:INCLUDES]->(m)
            """,
            parameters={
                "movie_id": movie.movie_id,
                "genres": genres
            })
    except Exception as e:
        logging.error(f"Failed to save or update movie: {e}")
        raise M2WDatabaseException("Unable to save or update movie.")


def get_all_movies_for_watchlist(tx: Transaction, watchlist_id: UUID) -> list[Movie]:
    """
    Retrieve all movies associated with a specific watchlist.

    This function queries the database using a transaction to get a list of
    movies that are part of a given watchlist. It requires the unique identifier
    of the watchlist and an active transaction object.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    watchlist_id : UUID
        The unique identifier of the watchlist for which movies are to be retrieved.

    Returns
    -------
    list[Movie]
        A list of `Movie` objects that belong to the specified watchlist.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        records = tx.run(
            query="""
                MATCH (:Watchlist {id: $watchlist_id})-[:MEMBER]->(:User)-[:VOTED {vote: "yeah"}]->(m:Movie)
                WITH DISTINCT m
                ORDER BY m.title
                RETURN
                    m.id as m_id,
                    m.title as m_title,
                    m.overview as m_overview,
                    m.duration as m_duration,
                    m.poster_path as m_poster_path,
                    COLLECT {
                        WITH m
                        MATCH (g:Genre)-[:INCLUDES]->(m)
                        ORDER BY g.name
                        RETURN g.id + "_" + g.name as name
                    } as m_genres,
                    m.official_trailer as m_official_trailer,
                    m.original_language as m_original_language,
                    m.release_date as m_release_date,
                    m.status as m_status,
                    m.updated_at as m_updated_at
            """,
            parameters={
                "watchlist_id": watchlist_id.hex
            }
        ).fetch(20480)
        result = []
        for record in records:
            result.append(Movie.from_record(record))
        return result
    except Exception as e:
        logging.error(f"Failed to get all movies for watchlist: {e}")
        raise M2WDatabaseException("Unable to get all movies for watchlist.")

def get_one_movie_by_id(tx: Transaction, movie_id: int) -> Movie:
    """
    Retrieve one movie by its unique identifier.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    movie_id : int
        The unique identifier of the movie.

    Returns
    -------
    Movie
        The `Movie` with the specified unique identifier.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        record = tx.run(
            query="""
                MATCH (m:Movie {id: $movie_id})
                WITH DISTINCT m
                RETURN
                    m.id as m_id,
                    m.title as m_title,
                    m.overview as m_overview,
                    m.duration as m_duration,
                    m.poster_path as m_poster_path,
                    COLLECT {
                        WITH m
                        MATCH (g:Genre)-[:INCLUDES]->(m)
                        ORDER BY g.name
                        RETURN g.id + "_" + g.name as name
                    } as m_genres,
                    m.official_trailer as m_official_trailer,
                    m.original_language as m_original_language,
                    m.release_date as m_release_date,
                    m.status as m_status,
                    m.updated_at as m_updated_at
            """,
            parameters={
                "movie_id": movie_id
            }
        ).single(strict=True)
        return Movie.from_record(record)
    except Exception as e:
        logging.error(f"Failed to get movie by id: {e}")
        raise M2WDatabaseException("Unable to get movie by id.")

def delete_details_of_obsolete_movies(tx: Transaction):
    """
    Deletes obsolete movies and their details from the database.

    This function operates on the database using a given transaction.
    It performs two main operations:
    1. Deletes movies that have no votes and no watch history, which are considered
       orphaned movies left over after their removal from all watchlists and updated more
       than 4 weeks ago.
    2. Removes detailed information of movies that have no votes but still exist in watch
       history and were updated more than 4 weeks ago. Only the IDs of such movies are
       retained to allow for potential re-adding later if required.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        # delete movies without any votes and watch history
        # these are orphaned movies which are left-over after deleting them from
        # the watchlists without ever watching them
        tx.run(
            query="""
                MATCH (m:Movie)
                WHERE NOT EXISTS((:User)-[]->(m)) AND m.updated_at < $four_weeks_ago
                DETACH DELETE m
            """,
            parameters={
                "four_weeks_ago": datetime.now() - timedelta(weeks=4)
            }
        )
        # delete movie details for those movies which have no votes but have watch history
        # we leave only the ids to be able to re-add them later if needed
        tx.run(
            query="""
                MATCH (m:Movie)
                WHERE NOT EXISTS((:User)-[:VOTED]->(m)) AND m.updated_at < $four_weeks_ago
                REMOVE
                    m.title,
                    m.overview,
                    m.duration,
                    m.poster_path,
                    m.genres,
                    m.official_trailer,
                    m.original_language,
                    m.release_date,
                    m.status,
                    m.updated_at
            """,
            parameters={
                "four_weeks_ago": datetime.now() - timedelta(weeks=4)
            }
        )
    except Exception as e:
        logging.error(f"Failed to delete details of obsolete movies: {e}")
        raise M2WDatabaseException("Unable to delete details of obsolete movies.")


def keep_movie_ids_where_update_is_needed(tx: Transaction, movie_ids: list[int]) -> list[int]:
    """
    Finds missing movies and movies where an update is needed.

    A movie is considered missing if it does not exist in the database or only the ID is saved in a stub.
    A movie is considered to need an update if it exists in the database but:
    1. The movie was released more than a month ago and was not updated in the last 4 weeks.
    2. The movie was released less than a month ago and was not updated in the last 1 day.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    movie_ids : list[int]
        The unique identifiers of the movies for which we need to check if an update is needed.

    Returns
    -------
    list[int]
        A list of movie ids that need an update.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    if (movie_ids is None) or (len(movie_ids) == 0):
        return []
    try:
        found_ids = tx.run(
            query="""
                MATCH (m:Movie)
                WHERE m.id IN $movie_ids
                AND m.release_date IS NOT NULL
                AND m.updated_at IS NOT NULL
                AND (
                    (m.release_date < $one_month_ago AND m.updated_at > $four_weeks_ago)
                    OR (m.release_date >= $one_month_ago AND m.updated_at > $one_day_ago)
                )
                RETURN m.id as m_id
            """,
            parameters={
                "movie_ids": movie_ids,
                "four_weeks_ago": datetime.now() - timedelta(weeks=4),
                "one_day_ago": datetime.now() - timedelta(days=1),
                "one_month_ago": date.today() - timedelta(days=31)
            }
        ).fetch(len(movie_ids))
        found = []
        for record in found_ids:
            found.append(record["m_id"])
        needs_update = list(set(movie_ids) - set(found))
        return needs_update
    except Exception as e:
        logging.error(f"Failed to find movies where update is needed: {e}")
        raise M2WDatabaseException("Unable to find movies where update is needed.")

