import logging

from neo4j import Transaction
from neo4j.exceptions import ResultNotSingleError

from src.dao.m2w_graph_db_entities import User, TmdbUser, M2WDatabaseException


def save_or_update_user(tx: Transaction, user: User):
    """
    Saves or updates a user in the database.

    This function either creates a new user or updates an existing one in the
    database. It performs a merge operation based on the user's unique ID, and
    updates their attributes such as email, locale, nickname, profile picture,
    and creation date.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user : User
        The user object containing the details to be saved or updated in 
        the database.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MERGE (u:User {id: $user.id})
                SET u = $user
            """,
            parameters={
                "user": {
                    "id": user.user_id,
                    "email": user.email,
                    "locale": user.locale,
                    "nickname": user.nickname,
                    "profile_pic": user.profile_pic,
                    "updated_at": user.updated_at,
                }
            })
    except Exception as e:
        logging.error(f"Failed to save or update user: {e}")
        raise M2WDatabaseException("Unable to save or update user.")


def get_one_user(tx: Transaction, user_id: str) -> User:
    """
    Retrieves the details of a single user from the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_id : str
        The unique identifier of the user to retrieve.

    Returns
    -------
    User
        An instance of the `User` object containing the retrieved user's details.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        record = tx.run(
            query="""
                MATCH (u:User {id: $user_id})
                RETURN 
                    u.id as u_id, 
                    u.email as u_email,
                    u.locale as u_locale,
                    u.nickname as u_nickname,
                    u.profile_pic as u_profile_pic,
                    u.updated_at as u_updated_at     
            """,
            parameters={
                "user_id": user_id
            }).single(strict=True)
        return User.from_record(record)
    except ResultNotSingleError as e:
        logging.debug(f"Failed to get one user: {e}")
        raise M2WDatabaseException("Unable to get one user.")


def save_or_update_tmdb_user(tx: Transaction, user: TmdbUser):
    """
    Save or update a TMDB user in the database. This function ensures that the TMDB
    user information is either added as a new record or updated if it already
    exists. It also creates a relationship between the TMDB user and an existing
    user if not already established.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user : TmdbUser
        An instance of TmdbUser containing all attributes and details necessary
        for saving or updating the TMDB user.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MATCH (u:User {id: $user_id})
                MERGE (t:TmdbUser {id: $tmdb_user.id})
                SET t = $tmdb_user
                MERGE (t)-[:CONNECTS]->(u)
            """,
            parameters={
                "user_id": user.user_id,
                "tmdb_user": {
                    "id": user.tmdb_id,
                    "session": user.session,
                    "include_adult": user.include_adult,
                    "iso_3166_1": user.iso_3166_1 if user.iso_3166_1 is not None else "",
                    "iso_639_1": user.iso_639_1 if user.iso_639_1 is not None else "",
                    "name": user.name if user.name is not None else "",
                    "username": user.username if user.username is not None else "",
                    "updated_at": user.updated_at,
                }
            })
    except Exception as e:
        logging.error(f"Failed to save or update TMDB user: {e}")
        raise M2WDatabaseException("Unable to save or update TMDB user.")


def get_one_tmdb_user(tx: Transaction, user_id: str) -> TmdbUser:
    """
    Retrieves the details of a single tmdb user from the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    user_id : str
        The unique identifier of the user to retrieve.

    Returns
    -------
    TmdbUser
        An instance of the `TmdbUser` object containing the retrieved user's details.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        record = tx.run(
            query="""
                MATCH (t:TmdbUser)-[:CONNECTS]->(u:User {id: $user_id})
                RETURN 
                    u.id as u_id, 
                    t.id as t_id, 
                    t.session as t_session,
                    t.include_adult as t_include_adult,
                    t.iso_3166_1 as t_iso_3166_1,
                    t.iso_639_1 as t_iso_639_1,
                    t.name as t_name,
                    t.username as t_username,
                    t.updated_at as t_updated_at
            """,
            parameters={
                "user_id": user_id
            }).single(strict=True)
        return TmdbUser.from_record(record)
    except ResultNotSingleError as e:
        logging.debug(f"Failed to get one TMDB user: {e}")
        raise M2WDatabaseException("Unable to get one TMDB user.")

def count_tmdb_users(tx: Transaction) -> int:
    """
    Retrieves the number of TMDB users in the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.

    Returns
    -------
    int
        the number of TMDB users

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        record = tx.run(
            query="""
                MATCH (t:TmdbUser)
                RETURN COUNT(t.id) as t_count
            """,
            ).single(strict=True)
        return record['t_count']
    except ResultNotSingleError as e:
        logging.debug(f"Failed to count TMDB users: {e}")
        raise M2WDatabaseException("Unable to count TMDB users.")


def get_tmdb_users(tx: Transaction, offset: int, limit: int) -> list[TmdbUser]:
    """
    Retrieves a page of TMDB user details from the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    offset : int
        The number of records to skip before retrieving the next page.
    limit : int
        The maximum number of records to retrieve in the page.

    Returns
    -------
    list[TmdbUser]
        A list of `TmdbUser` objects containing the details of the TMDB users.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        records = tx.run(
            query="""
                MATCH (t:TmdbUser)-[:CONNECTS]->(u:User)
                ORDER BY t.id ASC
                SKIP $offset
                LIMIT $limit
                RETURN 
                    u.id as u_id, 
                    t.id as t_id, 
                    t.session as t_session,
                    t.include_adult as t_include_adult,
                    t.iso_3166_1 as t_iso_3166_1,
                    t.iso_639_1 as t_iso_639_1,
                    t.name as t_name,
                    t.username as t_username,
                    t.updated_at as t_updated_at
            """,
            parameters={
                "offset": offset,
                "limit": limit
            }).fetch(limit)
        result = []
        for record in records:
            result.append(TmdbUser.from_record(record))
        return result
    except ResultNotSingleError as e:
        logging.debug(f"Failed to count TMDB users: {e}")
        raise M2WDatabaseException("Unable to count TMDB users.")