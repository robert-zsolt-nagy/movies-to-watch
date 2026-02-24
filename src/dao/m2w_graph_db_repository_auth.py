import hashlib
import logging
import uuid
from datetime import datetime

from neo4j import Transaction, Driver
from neo4j.exceptions import ResultNotSingleError
from requests import HTTPError

from src.dao.authentication_manager import AuthUser, AuthenticationManager, BaseAccountInfo
from src.dao.m2w_graph_db_entities import M2WDatabaseException


class Neo4jAuthenticationManager(AuthenticationManager):
    def __init__(self, driver: Driver):
        self.driver = driver

    def sign_in_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Signs in a user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.

        Returns
        -------
        AuthUser
            An authenticated user.
        """
        session = None
        tx = None
        try:
            session = self.driver.session()
            tx = session.begin_transaction()
            record = tx.run(
                query="""
                    MATCH (a:AuthUser {email: $email, password: $password})
                    RETURN 
                        a.id as user_id,
                        a.email as email,
                        a.id_token as id_token,
                        a.display_name as display_name,
                        a.refresh_token as refresh_token,
                        a.expires_in as expires_in  
                """,
                parameters={
                    "email": email,
                    "password": hashlib.sha256((password + email).encode()).hexdigest()
                }).single(strict=True)
            return AuthUser.from_record(record)
        except ResultNotSingleError as e:
            logging.debug(f"Failed to get one auth user: {e}")
            raise M2WDatabaseException("Unable to get one auth user.")
        finally:
            if tx:
                tx.commit()
            if session:
                session.close()

    def get_account_info(self, id_token: str) -> BaseAccountInfo:
        """Gets the account information of a signed-in user.

        Parameters
        ----------
        id_token: str
            the idToken of the signed-in user.

        Returns
        -------
        BaseAccountInfo
            The most crucial account information.
        """
        return BaseAccountInfo(
            email_verified=True,
            last_refresh_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )

    def create_user_with_email_and_password(self, email: str, password: str) -> AuthUser:
        """Creates a new user with email and password.

        Parameters
        ----------
        email: str
            the email of the user.
        password: str
            the password of the user.

        Returns
        -------
        AuthUser
            The data of the created user.
        """
        session = None
        tx = None
        try:
            session = self.driver.session()
            tx = session.begin_transaction()
            random_uuid = uuid.uuid4().hex
            tx.run(
                query="""
                    CREATE (a:AuthUser {id: $user.id})
                    SET a = $user
                """,
                parameters={
                    "user": {
                        "id": random_uuid,
                        "email": email,
                        "password": hashlib.sha256((password + email).encode()).hexdigest(),
                        "id_token": random_uuid,
                        "display_name": email,
                        "photo_url": "00.jpg",
                        "refresh_token": "refresh_token",
                        "expires_in": 3600,
                    }
                })
            record = tx.run(
                query="""
                    MATCH (a:AuthUser {email: $email, password: $password})
                    RETURN 
                        a.id as user_id,
                        a.email as email,
                        a.id_token as id_token,
                        a.display_name as display_name,
                        a.refresh_token as refresh_token,
                        a.expires_in as expires_in  
                """,
                parameters={
                    "email": email,
                    "password": hashlib.sha256((password + email).encode()).hexdigest()
                }).single(strict=True)
            return AuthUser.from_record(record)
        except Exception as e:
            logging.error(f"Failed to save or update auth user: {e}")
            raise M2WDatabaseException("Unable to save or update auth user.")
        finally:
            if tx:
                tx.commit()
            if session:
                session.close()

    def update_profile(self, id_token, display_name=None, photo_url=None, delete_attribute=None):
        """Updates a profile with new data.

        Parameters
        ----------
        id_token:
            A Firebase Auth ID token for the user.
        display_name:
            User's new display name.
        photo_url:
            User's new photo url.
        delete_attribute:
            List of attributes to delete, "DISPLAY_NAME" or "PHOTO_URL". This will nullify these values.

        """
        session = None
        tx = None
        try:
            session = self.driver.session()
            tx = session.begin_transaction()
            record = tx.run(
                query="""
                    MATCH (a:AuthUser {id_token: $id_token})
                    RETURN 
                        a.id as user_id,
                        a.email as email,
                        a.password as password,
                        a.photo_url as photo_url,
                        a.id_token as id_token,
                        a.display_name as display_name,
                        a.refresh_token as refresh_token,
                        a.expires_in as expires_in  
                """,
                parameters={
                    "id_token": id_token
                }).single(strict=True)
            saved = AuthUser.from_record(record)
            saved.password = record['password']
            saved.photo_url = record['photo_url']
            tx.run(
                query="""
                    MERGE (a:AuthUser {id: $user.id})
                    SET a = $user
                """,
                parameters={
                    "user": {
                        "id": saved.user_id,
                        "email": saved.email,
                        "password": saved.password,
                        "id_token": id_token,
                        "display_name": display_name,
                        "photo_url": photo_url,
                        "refresh_token": "refresh_token",
                        "expires_in": 3600,
                    }
                })
        except Exception as e:
            logging.error(f"Failed to save or update auth user: {e}")
            raise M2WDatabaseException("Unable to save or update auth user.")
        finally:
            if tx:
                tx.commit()
            if session:
                session.close()

    def send_email_verification(self, id_token):
        """Sends a new verification email for the user identified by id_token."""
        return True

    def send_password_reset_email(self, email):
        """Sends a password reset email to the provided email address."""
        return True

    
