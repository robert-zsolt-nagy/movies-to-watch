from datetime import date
from enum import Enum
from uuid import UUID

from src.dao.m2w_graph_db_entities import VoteValue, Vote, WatchHistory, Provider, ProviderFilter, AvailabilityType, \
    Availability, Movie, User, WatchList, TmdbUser, Genre


class VoteValueDto(Enum):
    YEAH = "yeah"
    NAH = "nah"

    @classmethod
    def from_request(cls, vote: str):
        if vote == "like":
            return cls.YEAH
        elif vote == "block":
            return cls.NAH
        else:
            raise ValueError("Invalid vote value: str")

    @classmethod
    def from_entity(cls, vote: VoteValue):
        return cls(vote.value)

    def to_entity(self) -> VoteValue:
        return VoteValue(self.value)


class VoteDto:
    def __init__(self,
                 user_id: str, movie_id: int, vote: VoteValueDto,
                 user_nickname: str | None = None, user_profile_pic: str | None = None):
        self.user_id = user_id
        self.user_nickname = user_nickname
        self.user_profile_pic = user_profile_pic
        self.movie_id = movie_id
        self.vote = vote

    def to_entity(self) -> Vote:
        return Vote(
            user_id=self.user_id,
            movie_id=self.movie_id,
            vote=self.vote.to_entity())

    @classmethod
    def from_entity(cls, entity: Vote):
        return VoteDto(
            user_id=entity.user_id,
            movie_id=entity.movie_id,
            vote=VoteValueDto.from_entity(entity.vote))

    @classmethod
    def from_entity_with_user(cls, entity: Vote, users: dict[str, User]):
        return VoteDto(
            user_id=entity.user_id,
            movie_id=entity.movie_id,
            vote=VoteValueDto.from_entity(entity.vote),
            user_nickname=users[entity.user_id].nickname,
            user_profile_pic=users[entity.user_id].profile_pic)


class WatchHistoryDto:
    def __init__(self,
                 user_id: str, movie_id: int):
        self.user_id = user_id
        self.movie_id = movie_id

    @classmethod
    def from_entity(cls, entity: WatchHistory):
        return WatchHistoryDto(
            user_id=entity.user_id,
            movie_id=entity.movie_id)

    def to_entity(self) -> WatchHistory:
        return WatchHistory(
            user_id=self.user_id,
            movie_id=self.movie_id)


class ProviderDto:
    def __init__(self,
                 provider_id: int, name: str, logo_path: str):
        self.provider_id = provider_id
        self.name = name
        self.logo_path = logo_path

    @classmethod
    def from_entity(cls, entity: Provider):
        return ProviderDto(
            provider_id=entity.provider_id,
            name=entity.name,
            logo_path=entity.logo_path)

    def to_entity(self) -> Provider:
        return Provider(
            provider_id=self.provider_id,
            name=self.name,
            logo_path=self.logo_path)


class ProviderFilterDto:
    def __init__(self,
                 provider_id: int, location: str, priority: int):
        self.provider_id = provider_id
        self.location = location
        self.priority = priority

    @classmethod
    def from_entity(cls, entity: ProviderFilter):
        return ProviderFilterDto(
            provider_id=entity.provider_id,
            location=entity.location,
            priority=entity.priority
        )

    def to_entity(self) -> ProviderFilter:
        return ProviderFilter(
            provider_id=self.provider_id,
            location=self.location,
            priority=self.priority
        )


class AvailabilityTypeDto(Enum):
    STREAM = "flatrate"
    RENT = "rent"
    BUY = "buy"
    ADS = "ads"
    FREE = "free"

    @classmethod
    def from_entity(cls, availability_type: AvailabilityType):
        return cls(availability_type.value)

    def to_entity(self) -> AvailabilityType:
        return AvailabilityType(self.value)


class AvailabilityDto:
    def __init__(self,
                 provider: ProviderDto, movie_id: int, location: str, watch_type: AvailabilityTypeDto):
        self.provider = provider
        self.movie_id = movie_id
        self.location = location
        self.watch_type = watch_type

    @classmethod
    def from_entity(cls, entity: Availability):
        return AvailabilityDto(
            provider=ProviderDto.from_entity(entity.provider),
            movie_id=entity.movie_id,
            location=entity.location,
            watch_type=AvailabilityTypeDto.from_entity(entity.watch_type))

    def to_entity(self) -> Availability:
        return Availability(
            provider=self.provider.to_entity(),
            movie_id=self.movie_id,
            location=self.location,
            watch_type=self.watch_type.to_entity())


class GenreDto:
    def __init__(self, genre_id: int, name: str):
        self.genre_id = genre_id
        self.name = name

    @classmethod
    def from_entity(cls, entity: Genre):
        return GenreDto(
            genre_id=entity.genre_id,
            name=entity.name
        )

    def to_entity(self) -> Genre:
        return Genre(
            genre_id=self.genre_id,
            name=self.name
        )


class MovieDto:
    def __init__(self,
                 movie_id: int, title: str, overview: str | None, duration: int | None, poster_path: str | None,
                 genres: list[GenreDto], official_trailer: str | None, original_language: str | None,
                 release_date: date | None, status: str, availabilities: list[AvailabilityDto] | None = None,
                 votes: list[VoteDto] | None = None, watch_history: list[WatchHistoryDto] | None = None,
                 current_user_id: str | None = None):
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
        self.tmdb_link = f"https://www.themoviedb.org/movie/{movie_id}"
        stream = []
        buy_or_rent = []
        if availabilities is not None:
            for availability in availabilities:
                if (availability.watch_type == AvailabilityTypeDto.STREAM
                      or availability.watch_type == AvailabilityTypeDto.ADS
                      or availability.watch_type == AvailabilityTypeDto.FREE):
                    stream.append(availability)
                elif (availability.watch_type == AvailabilityTypeDto.BUY
                      or availability.watch_type == AvailabilityTypeDto.RENT):
                    buy_or_rent.append(availability)
        self.providers = {
            "stream": stream,
            "buy_or_rent": buy_or_rent
        }
        genre_names = []
        for genre in self.genres:
            genre_names.append(genre.name)
        self.genre_names = ', '.join(genre_names)
        liked = []
        blocked = []
        voted = []
        my_vote = None
        if votes is not None:
            for vote in votes:
                if vote.movie_id != movie_id:
                    continue
                if vote.user_id == current_user_id:
                    my_vote = "liked" if vote.vote == VoteValueDto.YEAH else "blocked"
                elif vote.vote == VoteValueDto.YEAH:
                    liked.append(vote)
                elif vote.vote == VoteValueDto.NAH:
                    blocked.append(vote)
                voted.append(vote.user_id)
        self.votes = {
            "liked": liked,
            "blocked": blocked,
            "primary_vote": my_vote
        }
        i_watched = False
        if watch_history is not None:
            for w in watch_history:
                if w.movie_id != movie_id:
                    continue
                if (w.user_id not in voted) and (w.user_id == current_user_id):
                    i_watched = True
        self.watched = i_watched

    @classmethod
    def from_entity(cls,
                    movie: Movie, availabilities: list[Availability], votes: list[Vote], users: list[User],
                    watch_history: list[WatchHistory], current_user_id: str | None = None):
        movie_id = movie.movie_id
        title = movie.title
        overview = movie.overview
        duration = movie.duration
        poster_path = movie.poster_path
        genres = []
        for genre in movie.genres:
            genres.append(GenreDto.from_entity(genre))
        official_trailer = movie.official_trailer
        original_language = movie.original_language
        release_date = movie.release_date
        users_by_id = {}
        for user in users:
            users_by_id[user.user_id] = user
        availabilities_dto = []
        for availability in availabilities:
            availabilities_dto.append(AvailabilityDto.from_entity(availability))
        votes_dto = []
        for vote in votes:
            votes_dto.append(VoteDto.from_entity_with_user(entity=vote, users=users_by_id))
        watch_history_dto = []
        for watch_history_entry in watch_history:
            watch_history_dto.append(WatchHistoryDto.from_entity(watch_history_entry))
        status = movie.status
        return MovieDto(
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
            availabilities=availabilities_dto,
            votes=votes_dto,
            watch_history=watch_history_dto,
            current_user_id=current_user_id
        )

    def to_entity(self) -> Movie:
        genres = []
        for genre in self.genres:
            genres.append(genre.to_entity())
        return Movie(
            movie_id=self.movie_id,
            title=self.title,
            overview=self.overview,
            duration=self.duration,
            poster_path=self.poster_path,
            genres=genres,
            official_trailer=self.official_trailer,
            original_language=self.original_language,
            release_date=self.release_date,
            status=self.status,
        )


class TmdbUserDto:
    def __init__(self,
                 user_id: str, tmdb_id: int, session: str, include_adult: bool, iso_3166_1: str,
                 iso_639_1: str, username: str, name: str = ""):
        self.user_id = user_id
        self.tmdb_id = tmdb_id
        self.session = session
        self.include_adult = include_adult
        self.iso_3166_1 = iso_3166_1
        self.iso_639_1 = iso_639_1
        self.name = name
        self.username = username

    @classmethod
    def from_entity(cls, entity: TmdbUser):
        return TmdbUserDto(
            user_id=entity.user_id,
            tmdb_id=entity.tmdb_id,
            session=entity.session,
            include_adult=entity.include_adult,
            iso_3166_1=entity.iso_3166_1,
            iso_639_1=entity.iso_639_1,
            username=entity.username,
            name=entity.name
        )

    def to_entity(self) -> TmdbUser:
        return TmdbUser(
            user_id=self.user_id,
            tmdb_id=self.tmdb_id,
            session=self.session,
            include_adult=self.include_adult,
            iso_3166_1=self.iso_3166_1,
            iso_639_1=self.iso_639_1,
            username=self.username,
            name=self.name
        )


class UserDto:
    def __init__(self,
                 user_id: str, email: str, locale: str, nickname: str, profile_pic: str,
                 tmdb_user: TmdbUserDto | None = None):
        self.user_id = user_id
        self.email = email
        self.locale = locale
        self.nickname = nickname
        self.profile_pic = profile_pic
        self.tmdb_user = tmdb_user

    @classmethod
    def from_entity(cls, entity: User, tmdb_user: TmdbUser | None = None):
        tmdb_user_dto = TmdbUserDto.from_entity(tmdb_user) if tmdb_user is not None else None
        return UserDto(
            user_id=entity.user_id,
            email=entity.email,
            locale=entity.locale,
            nickname=entity.nickname,
            profile_pic=entity.profile_pic,
            tmdb_user=tmdb_user_dto)

    def to_entity(self) -> User:
        return User(
            user_id=self.user_id,
            email=self.email,
            locale=self.locale,
            nickname=self.nickname,
            profile_pic=self.profile_pic)


class WatchListDto:
    def __init__(self,
                 watchlist_id: UUID, name: str, provider_filters: list[ProviderFilterDto], users: list[UserDto]):
        self.watchlist_id = watchlist_id
        self.name = name
        self.users = users
        self.provider_filters = provider_filters

    @classmethod
    def from_entity(cls, entity: WatchList):
        users = []
        for user in entity.users:
            users.append(UserDto.from_entity(user))
        provider_filters = []
        for provider_filter in entity.provider_filters:
            provider_filters.append(ProviderFilterDto.from_entity(provider_filter))
        return WatchListDto(
            watchlist_id=entity.watchlist_id,
            name=entity.name,
            users=users,
            provider_filters=provider_filters
        )

    def to_entity(self) -> WatchList:
        users = []
        for user in self.users:
            users.append(user.to_entity())
        provider_filters = []
        for provider_filter in self.provider_filters:
            provider_filters.append(provider_filter.to_entity())
        return WatchList(
            watchlist_id=self.watchlist_id,
            name=self.name,
            users=users,
            provider_filters=provider_filters
        )
