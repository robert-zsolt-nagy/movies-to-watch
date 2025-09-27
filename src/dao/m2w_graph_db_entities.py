from datetime import datetime, date
from enum import Enum
from uuid import UUID

from neo4j import Record


class VoteValue(Enum):
    YEAH = "yeah"
    NAH = "nah"


class M2WDatabaseException(Exception):
    """Base class for Exceptions to M2WDatabase"""

    def __init__(self, message: str):
        """Base class for Exceptions to M2WDatabase"""
        super().__init__(message)

class Genre:
    def __init__(self, genre_id: int, name: str):
        self.genre_id = genre_id
        self.name = name

    @classmethod
    def from_record(cls, record: str):
        parts = record.split("_")
        return Genre(
            int(parts[0]),
            parts[1]
        )

    def __str__(self):
        return self.name

class Vote:
    def __init__(self,
                 user_id: str, movie_id: int, vote: VoteValue, updated_at: datetime = datetime.now()):
        self.user_id = user_id
        self.movie_id = movie_id
        self.vote = vote
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        user_id = record["u_id"]
        movie_id = record["m_id"]
        vote = VoteValue(record["v_vote"])
        updated_at = record["v_updated_at"]
        return Vote(
            user_id=user_id,
            movie_id=movie_id,
            vote=vote,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.user_id} {self.movie_id} {self.vote.value}"


class WatchHistory:
    def __init__(self,
                 user_id: str, movie_id: int, updated_at: datetime = datetime.now()):
        self.user_id = user_id
        self.movie_id = movie_id
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        user_id = record["u_id"]
        movie_id = record["m_id"]
        updated_at = record["h_updated_at"]
        return WatchHistory(
            user_id=user_id,
            movie_id=movie_id,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.user_id} {self.movie_id}"


class Provider:
    def __init__(self,
                 provider_id: int, name: str, logo_path: str,
                 updated_at: datetime = datetime.now()):
        self.provider_id = provider_id
        self.name = name
        self.logo_path = logo_path
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        provider_id = record["p_id"]
        name = record["p_name"]
        logo_path = record["p_logo_path"]
        updated_at = record["p_updated_at"]
        return Provider(
            provider_id=provider_id,
            name=name,
            logo_path=logo_path,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.provider_id} {self.name} {self.logo_path}"


class ProviderFilter:
    def __init__(self,
                 provider_id: int, location: str, priority: int,
                 updated_at: datetime = datetime.now()):
        self.provider_id = provider_id
        self.location = location
        self.priority = priority
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        provider_id = record["f_id"]
        location = record["f_location"]
        priority = record["f_priority"]
        updated_at = record["f_updated_at"]
        return ProviderFilter(
            provider_id=provider_id,
            location=location,
            priority=priority,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.provider_id} {self.location} {self.priority}"


class AvailabilityType(Enum):
    STREAM = "flatrate"
    RENT = "rent"
    BUY = "buy"
    ADS = "ads"
    FREE = "free"


class Availability:
    def __init__(self,
                 provider: Provider, movie_id: int, location: str, watch_type: AvailabilityType,
                 updated_at: datetime = datetime.now()):
        self.provider = provider
        self.movie_id = movie_id
        self.location = location
        self.watch_type = watch_type
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        movie_id = record["m_id"]
        location = record["a_location"]
        watch_type = AvailabilityType(record["a_watch_type"])
        updated_at = record["a_updated_at"]
        return Availability(
            provider=Provider.from_record(record),
            movie_id=movie_id,
            location=location,
            watch_type=watch_type,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.movie_id} {self.provider} {self.watch_type} {self.location}"


class Movie:
    def __init__(self,
                 movie_id: int, title: str, overview: str | None, duration: int | None, poster_path: str | None,
                 genres: list[Genre], official_trailer: str | None, original_language: str | None,
                 release_date: date | None, status: str, updated_at: datetime = datetime.now()):
        self.movie_id = movie_id
        self.title = title
        self.overview = overview
        self.duration = duration
        self.poster_path = poster_path
        self.genres = genres
        self.official_trailer = official_trailer
        self.original_language = original_language
        self.release_date = release_date
        self.status = status
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        movie_id = record["m_id"]
        title = record["m_title"]
        overview = record["m_overview"]
        duration = record["m_duration"]
        poster_path = record["m_poster_path"]
        genres = []
        for genre in record["m_genres"]:
            genres.append(Genre.from_record(genre))
        official_trailer = record["m_official_trailer"]
        original_language = record["m_original_language"]
        release_date = record["m_release_date"]
        status = record["m_status"]
        updated_at = record["m_updated_at"]
        return Movie(
            movie_id=movie_id,
            title=title,
            overview=overview,
            duration=duration,
            poster_path=poster_path,
            genres=genres,
            official_trailer=official_trailer,
            original_language=original_language,
            release_date=release_date,
            status=status,
            updated_at=updated_at)

    def __str__(self):
        return f"{self.movie_id} {self.title} {self.genres}"


class User:
    def __init__(self,
                 user_id: str, email: str, locale: str, nickname: str, profile_pic: str,
                 updated_at: datetime = datetime.now()):
        self.user_id = user_id
        self.email = email
        self.locale = locale
        self.nickname = nickname
        self.profile_pic = profile_pic
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        return User(
            user_id=record["u_id"],
            email=record["u_email"],
            locale=record["u_locale"],
            nickname=record["u_nickname"],
            profile_pic=record["u_profile_pic"],
            updated_at=record["u_updated_at"]
        )

    def __str__(self):
        return f"{self.user_id}"


class WatchList:
    def __init__(self,
                 watchlist_id: UUID, name: str, provider_filters: list[ProviderFilter],
                 updated_at: datetime = datetime.now(), users=None):
        if users is None:
            users = []
        self.watchlist_id = watchlist_id
        self.name = name
        self.users = users
        self.provider_filters = provider_filters
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        watchlist_id = UUID(hex=record["w_id"])
        name = record["w_name"]
        updated_at = record["w_updated_at"]
        return WatchList(
            watchlist_id=watchlist_id,
            name=name,
            provider_filters=[],
            updated_at=updated_at)

    def __str__(self):
        return f"{self.watchlist_id} {self.name} {self.provider_filters} {self.users}"


class TmdbUser:
    def __init__(self,
                 user_id: str, tmdb_id: int, session: str, include_adult: bool, iso_3166_1: str,
                 iso_639_1: str, username: str, name: str = "", updated_at: datetime = datetime.now()):
        self.user_id = user_id
        self.tmdb_id = tmdb_id
        self.session = session
        self.include_adult = include_adult
        self.iso_3166_1 = iso_3166_1
        self.iso_639_1 = iso_639_1
        self.name = name
        self.username = username
        self.updated_at = updated_at

    @classmethod
    def from_record(cls, record: Record):
        return TmdbUser(
            user_id=record["u_id"],
            tmdb_id=record["t_id"],
            session=record["t_session"],
            include_adult=record["t_include_adult"],
            iso_3166_1=record["t_iso_3166_1"],
            iso_639_1=record["t_iso_639_1"],
            name=record["t_name"],
            username=record["t_username"],
            updated_at=record["t_updated_at"]
        )

    def __str__(self):
        return f"{self.user_id} ${self.tmdb_id}"

