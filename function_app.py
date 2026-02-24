import logging
import os
import requests
import azure.functions as func
from typing import Optional
from neo4j import Driver, GraphDatabase

from src.dao.tmdb_http_client import TmdbHttpClient
from src.services.movie_caching import MovieCachingService

### dependencies ###
class SecretStore():
    """ Stores the secrets for the function """

    def __init__(self):
        """ Reads the secrets from the environment and stores them. """
        self.neo4j_uri = os.getenv("neo4j_uri")
        self.neo4j_user = os.getenv("neo4j_user")
        self.neo4j_pass = os.getenv("neo4j_pass")
        self.tmdb_token = os.getenv("tmdb_token")
        self.tmdb_api = os.getenv("tmdb_api")

SECRETS = SecretStore()

# connect to database
def connect_to_neo4j() -> Driver:
    """ Returns a properly set-up Driver instance. """
    uri = SECRETS.neo4j_uri
    auth = (SECRETS.neo4j_user, SECRETS.neo4j_pass)

    driver = GraphDatabase.driver(uri=uri, auth=auth)
    driver.verify_connectivity()
    return driver

DB_DRIVER = connect_to_neo4j()

def get_tmdb_http_client(session_: Optional[requests.Session] = None) -> TmdbHttpClient:
    """ Returns a properly set up TmdbHttpClient instance with the specified session."""
    return TmdbHttpClient(
        token=SECRETS.tmdb_token,
        base_url=SECRETS.tmdb_api,
        session=session_
    )

def get_movie_service() -> MovieCachingService:
    return MovieCachingService(
        tmdb_http_client=get_tmdb_http_client(),
        db=DB_DRIVER
    )

### Setting up function ###

app = func.FunctionApp()

@app.function_name(name="mytimer")
@app.timer_trigger(schedule="0 */15 * * * *", 
              arg_name="mytimer",
              run_on_startup=False) 
def update_movie_cache(mytimer: func.TimerRequest) -> None:
    """Updates the movie cache regularly."""
    try:
        logging.info("Movie cache update started.")
        get_movie_service().movie_cache_update_job()
    except Exception as e:
        logging.error(f"Movie cache error: {e}")
    else:
        logging.info("Movie cache update finished.")
