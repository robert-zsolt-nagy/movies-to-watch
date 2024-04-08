import tomllib

class SecretManager():
    """ Reads and manages the external secrets."""

    def __init__(self, secret_storage: str='secrets.toml') -> None:
        """ Open the secret storage and read the secrets."""
        with open(secret_storage, mode="rb") as vault:
            self.__SECRETS = tomllib.load(vault)

    @property
    def secrets(self) -> str:
        """ All of the secrets."""
        return self.__SECRETS
    
    @property
    def tmdb_rate_limit(self) -> str:
        """ The rate limit for tmdb requests."""
        return self.__SECRETS['tmdb']['rate_limit']
    
    @property
    def tmdb_token(self) -> str:
        """ The bearer token for authentication"""
        return self.__SECRETS['tmdb']['auth']['bearer_token']
    
    @property
    def tmdb_session(self) -> str:
        """ The session ID for authentication"""
        return self.__SECRETS['tmdb']['auth']['session_id']
    
    @property
    def tmdb_API(self) -> str:
        """ The base URL for the tmdb API."""
        return self.__SECRETS['tmdb']['URLs']['API_base_URL']
    
    @property
    def tmdb_home(self) -> str:
        """ The home URL for the tmdb."""
        return self.__SECRETS['tmdb']['URLs']['home_URL']
    
    @property
    def tmdb_image(self) -> str:
        """ The base URL for the tmdb image storage."""
        return self.__SECRETS['tmdb']['URLs']['image_URL']
    
    @property
    def firebase_cert(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firebase']['certificate']
    
    @property
    def firebase_config(self) -> str:
        """ The path to the firebase configuration."""
        return self.__SECRETS['firebase']['config']
    
    @property
    def firestore_cert(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firestore']['certificate']
    
    @property
    def firestore_project(self) -> str:
        """ The path to the firebase certificate."""
        return self.__SECRETS['firestore']['project']
    
    @property
    def m2w_base_URL(self) -> str:
        """ The base movies-to-watch URL."""
        return self.__SECRETS['m2w']['base_URL']
    
    @property
    def m2w_movie_retention(self) -> str:
        """ The base movies-to-watch URL."""
        return self.__SECRETS['m2w']['movie_retention']