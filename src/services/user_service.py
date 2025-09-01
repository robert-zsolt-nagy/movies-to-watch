from neo4j import Driver
from requests.exceptions import HTTPError

from src.dao.authentication_manager import AuthenticationManager, AuthUser, BaseAccountInfo
from src.dao.m2w_graph_db_entities import M2WDatabaseException, TmdbUser, User
from src.dao.m2w_graph_db_repository_users import get_one_user, get_one_tmdb_user, save_or_update_tmdb_user, \
    save_or_update_user
from src.dao.tmdb_user_repository import TmdbUserRepository, TmdbRequestToken
from src.services.m2w_dtos import UserDto


class UserManagerException(Exception):
    """Base class for exceptions in the User Manager Service."""


class EmailMismatchError(UserManagerException):
    """Email and confirm Email does not match."""


class PasswordMismatchError(UserManagerException):
    """Password and confirm password does not natch."""


class WeakPasswordError(UserManagerException):
    """Password should contain at least 6 characters."""


class UserManagerService:
    """Handles the user administration."""

    def __init__(
            self,
            db: Driver,
            auth: AuthenticationManager,
            user_repo: TmdbUserRepository
    ) -> None:
        """Handles the user administration.
        
        Parameters
        ----------
        db: Driver
            The Neo4j driver.
        auth: AuthenticationManager
            object that provides the authentication service.
        user_repo: TmdbUserRepository
            object that bundles the user related TMDB requests.
        """
        self.db = db
        self.auth = auth
        self.user_repo = user_repo

    def get_m2w_user_profile_data(self, user_id: str) -> UserDto:
        """
        Get the cached profile data for the user.
        
        Parameters
        ----------
        user_id: str
            the M2W ID of the user.

        Returns
        -------
        UserDto
            The cached profile data including the TMDB User details.

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
            user = get_one_user(tx=tx, user_id=user_id)
            try:
                tmdb_user = get_one_tmdb_user(tx=tx, user_id=user_id)
            except M2WDatabaseException:
                tmdb_user = None
            result = UserDto.from_entity(user, tmdb_user)
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"Failed to get user profile data: {e}")
        else:
            tx.commit()
            return result
        finally:
            if session is not None:
                session.close()

    def get_firebase_user_account_info(self, user_id_token: str) -> BaseAccountInfo:
        """Get the firebase account info for the user.
        
        Parameters
        ----------
        user_id_token: str
            the idToken of the signed-in user.

        Returns
        -------
        BaseAccountInfo
            the account info of the user.
        """
        return self.auth.get_account_info(id_token=user_id_token)

    def sign_in_user(self, email: str, password: str) -> AuthUser:
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
        return self.auth.sign_in_with_email_and_password(email=email, password=password)

    def update_profile_picture(self, user_id: str, profile_pic: str) -> None:
        """
        Creates or updates a user. If the user exists, updates the profile picture.
        
        Parameters
        ----------
        user_id: str 
            the ID of the document in the database.
        profile_pic: str
            the new profile picture filename.

        Raises
        ------
        UserManagerException:
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            user = get_one_user(tx=tx, user_id=user_id)
            user.profile_pic = profile_pic
            save_or_update_user(tx=tx, user=user)
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"Failed to update profile picture: {e}")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()

    def get_tmdb_account_data(self, user_id: str, session_id: str) -> TmdbUser:
        """ Gets the account data of a TMDB user.
        
        Parameters
        ----------
        user_id: str
            the M2W ID of the user.
        session_id: str
            the current session ID.

        Returns
        -------
            The received response as a dictionary that contains the account's data.
        """
        tmdb_user_data = self.user_repo.get_account_data(session_id=session_id)
        return TmdbUser(
            user_id=user_id,
            tmdb_id=tmdb_user_data["id"],
            username=tmdb_user_data["username"],
            session=session_id,
            include_adult=tmdb_user_data["include_adult"] if tmdb_user_data["include_adult"] is not None else False,
            iso_3166_1=tmdb_user_data["iso_3166_1"] if tmdb_user_data["iso_3166_1"] is not None else "",
            iso_639_1=tmdb_user_data["iso_639_1"] if tmdb_user_data["iso_639_1"] is not None else "",
            name=tmdb_user_data["name"] if tmdb_user_data["name"] is not None else ""
        )

    def sign_in_and_update_tmdb_cache(self, email: str, password: str) -> dict:
        """Signs in the user and updates the tmdb cache if necessary.

        Parameters
        ----------
        email: the email of the user.
        password: the password of the user.
        
        Returns
        -------
        The user data for session as dict.

        Raises
        ------
        UserManagerException in case of firebase errors during requests.
        """
        try:
            user = self.sign_in_user(email=email, password=password)
            account_info = self.auth.get_account_info(id_token=user.id_token)
            response = user.to_dict(account_info=account_info)
            self.update_tmdb_user_cache(user_id=user.user_id)
        except HTTPError as he:
            msg = self.auth.get_authentication_error_msg(he)
            raise UserManagerException(msg)
        else:
            return response

    def update_tmdb_user_cache(self, user_id: str) -> None:
        """Update the TMDB related data of user in the M2W database.
        
        Parameters
        ----------
        user_id: str
            the ID of the user in M2W database.

        Raises
        -------
        UserManagerException:
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            try:
                tmdb_user = get_one_tmdb_user(tx=tx, user_id=user_id)
            except M2WDatabaseException:
                # no TMDB user found, return without updating cache
                return
            tmdb_user = self.get_tmdb_account_data(user_id=user_id, session_id=tmdb_user.session)
            save_or_update_tmdb_user(tx=tx, user=tmdb_user)
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"Failed to update tmdb user cache: {e}")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()

    def create_tmdb_session_for_user(self, user_id: str, request_token: TmdbRequestToken) -> None:
        """ Create a session id for a particular request token of a user.
        
        Parameters
        ----------
        user_id: str
            the id of the current user.
        request_token: TmdbRequestToken
            the response received after requesting a new token for the user.

        Raises
        -------
        UserManagerException:
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            tmdb_session = self.user_repo.create_session_id(request_token=request_token)
            tmdb_user_data = self.get_tmdb_account_data(user_id=user_id, session_id=tmdb_session)
            save_or_update_tmdb_user(tx, tmdb_user_data)
        except Exception as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"Failed to create TMDB session: {e}")
        else:
            tx.commit()
        finally:
            if session is not None:
                session.close()

    def send_firebase_email_verification(self, id_token: str):
        """Send a new verification email for the user identified by id_token.
        
        Parameters
        ----------
        id_token: str
            the ID token of the user who needs a verification email.
        """
        return self.auth.send_email_verification(id_token=id_token)

    def sign_up_user(
            self,
            email: str,
            confirm_email: str,
            password: str,
            confirm_password: str,
            nickname: str,
            picture: str = "01.png",
            locale: str = "HU"
    ) -> bool:
        """Validate the sign-up form and create the user if valid.
        
        Parameters
        ----------
        email: str
            the email of the user.
        confirm_email: str
            the email of the user repeated.
        password: str
            the password of the user.
        confirm_password: str
            the password of the user repeated.
        nickname: str
            the nickname of the user.
        picture: str
            the filename of the chosen profile picture.
        locale: str
            the two-character locale ID of the user's locale.

        Returns
        -------
        bool
            True if successful.

        Raises
        ------
        EmailMismatchError:
            if email and confirm_email don't match.
        PasswordMismatchError:
            if password and confirm_password don't match.
        WeakPasswordError:
            if the password is shorter than 6 characters.
        HttpError:
            if firebase raises INVALID_EMAIL, MISSING_PASSWORD, INVALID_LOGIN_CREDENTIALS,
            EMAIL_EXISTS or WEAK_PASSWORD

        """
        if email != confirm_email:
            raise EmailMismatchError()

        if password != confirm_password:
            raise PasswordMismatchError()

        if len(password) < 6:
            raise WeakPasswordError()

        # create a user and add details
        my_user = self.auth.create_user_with_email_and_password(
            email=email,
            password=password
        )
        self.auth.update_profile(
            id_token=my_user.id_token,
            display_name=nickname
        )
        # send verification email for profile
        self.send_firebase_email_verification(id_token=my_user.id_token)
        session = None
        tx = None
        try:
            # upsert user profile in M2W database
            user = User(
                user_id=my_user.user_id,
                email=email,
                nickname=nickname,
                locale=locale,
                profile_pic=picture
            )
            session = self.db.session()
            tx = session.begin_transaction()
            save_or_update_user(tx=tx, user=user)
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"Failed to get save user data: {e}")
        else:
            tx.commit()
            return True
        finally:
            if session is not None:
                session.close()

    def get_tmdb_request_token(self) -> TmdbRequestToken:
        """
        Get the request token for linking the user's M2W and TMDB profiles.
        Initiate linking the user's M2W and TMDB profiles.
        
        Returns
        -------
        TmdbRequestToken
            The created tmdb request token.

        Raises
        ------
        UserManagerException
            if the operation fails.
        """
        try:
            return self.user_repo.create_request_token()
        except Exception as e:
            raise UserManagerException(f"Failed to get request token: {e}")

    def get_tmdb_permission_url(
            self,
            tmdb_request_token: TmdbRequestToken,
            redirect_to: str | None = None,
            tmdb_url: str = "https://www.themoviedb.org"
    ) -> str:
        """Initiate linking the user's M2W and TMDB profiles.

        Parameters
        ----------
        tmdb_request_token: TmdbRequestToken
            the request token of the TMDB user.
        redirect_to: str | None
            the URL to redirect to after the approval process.
        tmdb_url: str
            the base URL of TMDB.

        Returns
        -------
        str
            the permission URL for the user to approve the link.
        """
        permission_url = self.user_repo.get_user_permission_url(
            redirect_to=redirect_to,
            tmdb_url=tmdb_url,
            request_token=tmdb_request_token
        )
        return permission_url

    def add_movie_to_users_watchlist(self, movie_id: int, user_id: str) -> bool:
        """Adds a movie to the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: int
            the ID of the movie in M2W.
        user_id: str
            the M2W ID of the user.

        Returns
        --------
        bool
            True if successful, False otherwise.

        Raises
        ------
        UserManagerException:
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            tmdb_user = get_one_tmdb_user(tx=tx, user_id=user_id)
            response_watchlist = self.user_repo.add_movie_to_watchlist(
                movie_id=movie_id,
                user_id=tmdb_user.tmdb_id,
                session_id=tmdb_user.session
            )
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"TMDB data of user is missing: {e}")
        else:
            tx.commit()
            return response_watchlist["success"]
        finally:
            if session is not None:
                session.close()

    def remove_movie_from_users_watchlist(self, movie_id: int, user_id: str) -> bool:
        """Remove a movie from the movie watchlist of a user.
        
        Parameters
        ----------
        movie_id: int
            the ID of the movie in M2W.
        user_id: str
            the M2W ID of the user.

        Returns
        --------
        bool
            True if successful, False otherwise.

        Raises
        ------
        UserManagerException:
            if the operation fails.
        """
        session = None
        tx = None
        try:
            session = self.db.session()
            tx = session.begin_transaction()
            tmdb_user = get_one_tmdb_user(tx=tx, user_id=user_id)
            response_watchlist = self.user_repo.remove_movie_from_watchlist(
                movie_id=movie_id,
                user_id=tmdb_user.tmdb_id,
                session_id=tmdb_user.session
            )
        except M2WDatabaseException as e:
            if tx is not None:
                tx.rollback()
            raise UserManagerException(f"TMDB data of user is missing: {e}")
        else:
            tx.commit()
            return response_watchlist["success"]
        finally:
            if session is not None:
                session.close()
