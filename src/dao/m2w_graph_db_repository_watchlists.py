import logging
from datetime import datetime
from uuid import UUID

from neo4j import Transaction
from neo4j.exceptions import ResultNotSingleError

from src.dao.m2w_graph_db_entities import User, WatchList, ProviderFilter, M2WDatabaseException


def save_or_update_watchlist(tx=Transaction, watchlist=WatchList):
    """
    Save or update a watchlist.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    watchlist : WatchList
        A watchlist containing all attributes we want to save.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MERGE (w:Watchlist {id: $watchlist_id})
                SET 
                    w.name = $name, 
                    w.updated_at = $updated_at
            """,
            parameters={
                "watchlist_id": watchlist.watchlist_id.hex,
                "name": watchlist.name,
                "updated_at": watchlist.updated_at
            }
        )
        # delete any existing filters
        tx.run(
            query="""
                MATCH (w:Watchlist {id: $watchlist_id})-[f:FOLLOWS]->(:Provider)
                DELETE f
            """,
            parameters={
                "watchlist_id": watchlist.watchlist_id.hex
            }
        )
        # save new filters
        if watchlist.provider_filters is not None and len(watchlist.provider_filters) > 0:
            filters = []
            for pf in watchlist.provider_filters:
                filters.append({
                    "provider_id": pf.provider_id,
                    "location": pf.location,
                    "priority": pf.priority,
                    "updated_at": pf.updated_at
                })
            tx.run(
                query="""
                    UNWIND $filters AS filter
                    MATCH (p:Provider {id: filter.provider_id}),(w:Watchlist {id: $watchlist_id})
                    MERGE (w)-[f:FOLLOWS {location: filter.location}]->(p)
                    SET 
                        f.priority = filter.priority,
                        f.updated_at = filter.updated_at
                """,
                parameters={
                    "watchlist_id": watchlist.watchlist_id.hex,
                    "filters": filters
                }
            )
    except Exception as e:
        logging.debug(f"Failed to save watchlist: {e}")
        raise M2WDatabaseException("Unable to save watchlist.")


def get_primary_watchlist_id(tx: Transaction, user_id: str) -> UUID:
    """
    Retrieve the primary watchlist ID for a user.

    Parameters
    ----------
    tx: Transaction
        The Neo4j transaction object.
    user_id: str
        The unique identifier of the user.

    Returns
    -------
    UUID
        The primary watchlist ID for the user.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.

    """
    try:
        record = tx.run(
            query="""
                MATCH (w:Watchlist)-[m:MEMBER]->(:User {id: $user_id})
                ORDER BY m.primary ASC, m.updated_at ASC
                LIMIT 1
                RETURN w.id as w_id
            """,
            parameters={
                "user_id": user_id
            }
        ).single(strict=True)
        return UUID(hex=record["w_id"])
    except ResultNotSingleError as e:
        logging.debug(f"Failed to find primary watchlist of user={user_id}: {e}")
        raise M2WDatabaseException("Unable to find primary watchlist of user.")


def add_user_to_watchlist(tx: Transaction, watchlist_id: UUID, user_id: str, primary: bool = True):
    """
    Adds the user to a watchlist.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    watchlist_id : UUID
        The unique identifier of the watchlist for which details are to be retrieved.
    user_id: str
        The unique identifier of the user to be added to the watchlist.
    primary: bool
        Whether this group should become the primary group for the user or not.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MATCH (w:Watchlist {id: $watchlist_id}),(u:User {id: $user_id})
                MERGE (w)-[m:MEMBER]->(u)
                SET m.updated_at = $updated_at
                RETURN m.updated_at as m_updated_at
            """,
            parameters={
                "watchlist_id": watchlist_id.hex,
                "user_id": user_id,
                "updated_at": datetime.now()
            }
        ).single(strict=True)
        if primary:
            tx.run(
                query="""
                    MATCH (:Watchlist)-[m:MEMBER]->(:User {id: $user_id})
                    SET m.primary = false
                """,
                parameters={
                    "user_id": user_id
                }
            )
            tx.run(
                query="""
                    MATCH (w:Watchlist {id: $watchlist_id})-[m:MEMBER]->(:User {id: $user_id})
                    SET m.primary = true
                """,
                parameters={
                    "watchlist_id": watchlist_id.hex,
                    "user_id": user_id
                }
            )
    except ResultNotSingleError as e:
        logging.debug(f"Failed to add user={user_id} to watchlist={watchlist_id}: {e}")
        raise M2WDatabaseException("Unable to add user to watchlist.")


def get_watchlist_details(tx: Transaction, watchlist_id: UUID) -> WatchList:
    """
    Retrieves base watchlist details from the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    watchlist_id : UUID
        The unique identifier of the watchlist for which details are to be retrieved.

    Returns
    -------
    WatchList
        The watchlist details.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        watchlist_record = tx.run(
            query="""
                MATCH (w:Watchlist {id: $watchlist_id})
                RETURN
                    w.id as w_id,
                    w.name as w_name,
                    w.updated_at as w_updated_at
            """,
            parameters={
                "watchlist_id": watchlist_id.hex
            }
        ).single(strict=True)
        watchlist = WatchList.from_record(watchlist_record)
        filter_records = tx.run(
            query="""
                MATCH (:Watchlist {id: $watchlist_id})-[f:FOLLOWS]->(p:Provider)
                WITH DISTINCT f, p
                RETURN
                    p.id as f_id,
                    f.location as f_location,
                    f.priority as f_priority,
                    f.updated_at as f_updated_at
            """,
            parameters={
                "watchlist_id": watchlist_id.hex
            }
        ).fetch(20480)
        filters = []
        for record in filter_records:
            filters.append(ProviderFilter.from_record(record))
        watchlist.provider_filters = filters

        user_records = tx.run(
            query="""
                MATCH (:Watchlist {id: $watchlist_id})-[:MEMBER]->(u:User)
                RETURN
                    u.id as u_id, 
                    u.email as u_email,
                    u.locale as u_locale,
                    u.nickname as u_nickname,
                    u.profile_pic as u_profile_pic,
                    u.updated_at as u_updated_at     
            """,
            parameters={
                "watchlist_id": watchlist_id.hex
            }
        ).fetch(20480)
        users = []
        for record in user_records:
            users.append(User.from_record(record))
        watchlist.users = users

        return watchlist
    except Exception as e:
        logging.error(f"Failed to get details for watchlist: {e}")
        raise M2WDatabaseException("Unable to get details for watchlist.")


def get_all_provider_filters(tx: Transaction) -> list[ProviderFilter]:
    """
    Retrieves all provider filters from the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.

    Returns
    -------
    list[ProviderFilter]
        A list of provider filters.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        filter_records = tx.run(
            query="""
                MATCH (:Watchlist)-[f:FOLLOWS]->(p:Provider)
                ORDER BY p.id, f.priority
                RETURN DISTINCT 
                    p.id as f_id, 
                    f.location as f_location,
                    f.priority as f_priority, 
                    p.updated_at as f_updated_at
            """
        ).fetch(20480)
        filters = []
        for record in filter_records:
            filters.append(ProviderFilter.from_record(record))
        return filters
    except Exception as e:
        logging.error(f"Failed to get details for provider filters: {e}")
        raise M2WDatabaseException("Unable to get details for provider filters.")
