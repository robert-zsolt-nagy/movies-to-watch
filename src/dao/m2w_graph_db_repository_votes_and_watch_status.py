import logging
from datetime import datetime
from typing import List

from neo4j import Transaction
from neo4j.exceptions import ResultNotSingleError

from src.dao.m2w_graph_db_entities import VoteValue, Vote, M2WDatabaseException, WatchHistory


def vote_for_movie(tx: Transaction, user_id: str, movie_id: int, vote_value: VoteValue) -> Vote:
    """
    Register a vote for a movie by a specific user.

    This method allows a user to cast a vote on a specific movie.
    It is expected that the method will appropriately process and
    store the vote associated with the provided movie and user ids.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_id : str
        The unique identifier of the user who is casting the vote.
    movie_id : int
        The unique identifier of the movie being voted on.
    vote_value : VoteValue
        The vote being cast by the user for the movie, which contains the
        relevant vote data or type.

    Returns
    -------
    Vote
        The vote being cast by the user for the movie

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """

    try:
        record = tx.run(
            query="""
                MATCH (u:User {id: $user_id}),(m:Movie {id: $movie_id})
                MERGE (u)-[v:VOTED]->(m)
                SET v.vote = $vote,
                    v.updated_at = $updated_at
                RETURN u.id as u_id, m.id as m_id, v.vote as v_vote, v.updated_at as v_updated_at
            """,
            parameters={
                "user_id": user_id,
                "movie_id": movie_id,
                "vote": vote_value.value,
                "updated_at": datetime.now()
            }).single(strict=True)
        return Vote.from_record(record)
    except ResultNotSingleError as e:
        logging.error(f"Failed to record vote: {e}")
        raise M2WDatabaseException("Unable to record vote.")


def get_all_votes_of_watchlist(tx: Transaction, user_ids: list[str], movie_ids: list[int]) -> List[Vote]:
    """
    Get all votes for a watchlist.
    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_ids : list[str]
        The unique identifiers of the users we want to get votes from.
    movie_ids : list[int]
        The unique identifiers of the movies we want to get votes for.

    Returns
    -------
    List[Vote]
        The list of votes for a watchlist.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """

    try:
        records = tx.run(
            query="""
                MATCH (u:User)-[v:VOTED]->(m:Movie)
                WHERE u.id IN $user_ids AND m.id IN $movie_ids
                RETURN u.id as u_id, m.id as m_id, v.vote as v_vote, v.updated_at as v_updated_at
            """,
            parameters={
                "user_ids": user_ids,
                "movie_ids": movie_ids
            }
        ).fetch(20480)
        result = []
        for record in records:
            result.append(Vote.from_record(record))
        return result
    except Exception as e:
        logging.error(f"Failed to get all votes for watchlist: {e}")
        raise M2WDatabaseException("Unable to get all votes for watchlist.")


def get_all_watch_history_of_watchlist(tx: Transaction, user_ids: list[str], movie_ids: list[int]) -> List[WatchHistory]:
    """
    Get all watch history for a watchlist.
    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_ids : list[str]
        The unique identifiers of the users we want to get votes from.
    movie_ids : list[int]
        The unique identifiers of the movies we want to get the watch history for.

    Returns
    -------
    List[WatchHistory]
        The list of watch history for a watchlist.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """

    try:
        records = tx.run(
            query="""
                MATCH (u:User)-[w:WATCHED]->(m:Movie)
                WHERE u.id IN $user_ids AND m.id IN $movie_ids
                RETURN u.id as u_id, m.id as m_id, w.updated_at as h_updated_at
            """,
            parameters={
                "user_ids": user_ids,
                "movie_ids": movie_ids
            }
        ).fetch(20480)
        result = []
        for record in records:
            result.append(WatchHistory.from_record(record))
        return result
    except Exception as e:
        logging.error(f"Failed to get all watch history for watchlist: {e}")
        raise M2WDatabaseException("Unable to get all watch history for watchlist.")


def mark_movie_as_watched(tx: Transaction, user_id: str, movie_id: int):
    """
    Remove the vote for a movie by a specific user and mark it as watched.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_id : str
        The unique identifier of the user who is casting the vote.
    movie_id : int
        The unique identifier of the movie being voted on.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MATCH (u:User {id: $user_id}),(m:Movie {id: $movie_id})
                MERGE (u)-[w:WATCHED]->(m)
                SET w.updated_at = $updated_at
                WITH u, m
                MATCH (u)-[v:VOTED]->(m)
                DELETE v
            """,
            parameters={
                "user_id": user_id,
                "movie_id": movie_id,
                "updated_at": datetime.now()
        })
    except ResultNotSingleError as e:
        logging.debug(f"Failed to mark movie as watched: {e}")
        raise M2WDatabaseException("Unable to mark movie as watched.")
