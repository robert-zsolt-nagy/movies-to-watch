import logging
from uuid import UUID

from neo4j import Transaction

from src.dao.m2w_graph_db_entities import User, Availability, WatchList, \
    ProviderFilter, M2WDatabaseException, Provider


def save_or_update_provider(tx: Transaction, provider: Provider):
    """
    Saves or updates a provider in the database.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    provider : Provider
        The provider with all its details.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        tx.run(
            query="""
                MERGE (p:Provider {id: $provider.id})
                SET p = $provider
            """,
            parameters={
                "provider": {
                    "id": provider.provider_id,
                    "name": provider.name,
                    "logo_path": provider.logo_path,
                    "updated_at": provider.updated_at
                }
            }
        )
    except Exception as e:
        logging.debug(f"Failed to save or update provider: {e}")
        raise M2WDatabaseException("Unable to save or update provider.")


def save_movie_availabilities(tx: Transaction, movie_id: int, availabilities: list[Availability]):
    """
    Removes all availabilities for a movie and saves the provided new ones.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    movie_id : int
        The unique identifier of the movie for which availabilities are to be saved.
    availabilities : list[Availability]
        The list of availabilities to be saved.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        # delete all availabilities for the movie
        tx.run(
            query="""
                MATCH (m:Movie {id: $movie_id})<-[a:CARRIES]-(:Provider)
                DELETE a
            """,
            parameters={
                "movie_id": movie_id
            }
        )
        # save the new availabilities if any
        if (availabilities is not None) and (len(availabilities) > 0):
            a = []
            p = []
            for av in availabilities:
                a.append({
                    "provider_id": av.provider.provider_id,
                    "location": av.location,
                    "watch_type": av.watch_type.value,
                    "updated_at": av.updated_at
                })
                p.append({
                    "id": av.provider.provider_id,
                    "name": av.provider.name,
                    "logo_path": av.provider.logo_path,
                    "updated_at": av.provider.updated_at
                })
            tx.run(
                query="""
                    UNWIND $providers AS provider
                    MERGE (p:Provider {id: provider.id})
                    SET p = provider
                """,
                parameters={
                    "providers": p
                }
            )
            tx.run(
                query="""
                    MATCH (m:Movie {id: $movie_id})
                    WITH m
                    UNWIND $availabilities AS a
                    MATCH (p:Provider {id: a.provider_id})
                    MERGE (p)-[c:CARRIES {watch_type: a.watch_type, location: a.location}]->(m)
                    SET c.updated_at = a.updated_at
                """,
                parameters={
                    "movie_id": movie_id,
                    "availabilities": a
                }
            )
    except Exception as e:
        logging.error(f"Failed to save or update the availabilities of the movie: {movie_id}. {e}")
        raise M2WDatabaseException("Unable to save or update the availabilities of the movie.")


def get_all_availabilities_for_movies(
        tx: Transaction, movie_ids: list[int],
        provider_filters: list[ProviderFilter] | None = None) -> list[Availability]:
    """
    Retrieves all availability records associated with the given movies.

    Parameters
    ----------
    tx : Transaction
        The Neo4j transaction object.
    movie_ids : list[int]
        The unique identifiers of the movies for which availabilities are to be retrieved.
    provider_filters : list[ProviderFilter] | None, optional
        The providers and locations for which availabilities are to be retrieved, by default all are included.

    Returns
    -------
    list[Availability]
        A list of availability records related to the watchlist.

    Raises
    ------
    M2WDatabaseException
        If the operation fails.
    """
    try:
        if provider_filters is None:
            records = tx.run(
                query="""
                    MATCH (p:Provider)-[a:CARRIES]->(m:Movie)
                    WHERE m.id IN $movie_ids
                    WITH DISTINCT m, p, a
                    ORDER BY m.id, p.name, a.location, a.watch_type
                    RETURN
                        p.id as p_id,
                        p.name as p_name,
                        p.logo_path as p_logo_path,
                        p.updated_at as p_updated_at,
                        m.id as m_id,
                        a.location as a_location,
                        a.watch_type as a_watch_type,
                        a.updated_at as a_updated_at
                """,
                parameters={
                    "movie_ids": movie_ids
                }
            ).fetch(20480)
        else:
            filters = []
            for pf in provider_filters:
                filters.append(f"{pf.provider_id}_{pf.location}")
            records = tx.run(
                query="""
                    MATCH (p:Provider)-[a:CARRIES]->(m:Movie)
                    WHERE m.id IN $movie_ids
                    AND p.id + '_' + a.location IN $provider_filters
                    WITH DISTINCT m, p, a
                    ORDER BY m.id, p.name, a.location, a.watch_type
                    RETURN
                        p.id as p_id,
                        p.name as p_name,
                        p.logo_path as p_logo_path,
                        p.updated_at as p_updated_at,
                        m.id as m_id,
                        a.location as a_location,
                        a.watch_type as a_watch_type,
                        a.updated_at as a_updated_at
                """,
                parameters={
                    "movie_ids": movie_ids,
                    "provider_filters": filters
                }
            )
        result = []
        for record in records:
            result.append(Availability.from_record(record))
        return result
    except Exception as e:
        logging.error(f"Failed to get all movie availabilities for watchlist: {e}")
        raise M2WDatabaseException("Unable to get all movie availabilities for watchlist.")
