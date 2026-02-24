from unittest import TestCase
from datetime import date
from uuid import uuid4

from src.services.m2w_dtos import (
    VoteValueDto,
    VoteDto,
    WatchHistoryDto,
    ProviderDto,
    ProviderFilterDto,
    AvailabilityTypeDto,
    AvailabilityDto,
    GenreDto,
    MovieDto,
    TmdbUserDto,
    UserDto,
    WatchListDto,
)
from src.dao.m2w_graph_db_entities import (
    VoteValue,
    Vote,
    WatchHistory,
    Provider,
    ProviderFilter,
    AvailabilityType,
    Availability,
    Genre,
    Movie,
    User,
    WatchList,
    TmdbUser,
)


class TestDtos(TestCase):
    def test_vote_value_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        value_yeah = VoteValue.YEAH
        value_nah = VoteValue.NAH
        # when
        yeah = VoteValueDto.from_entity(value_yeah)
        nah = VoteValueDto.from_entity(value_nah)
        # then
        self.assertEqual(yeah, VoteValueDto.YEAH)
        self.assertEqual(nah, VoteValueDto.NAH)

    def test_vote_value_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        value_yeah = VoteValueDto.YEAH
        value_nah = VoteValueDto.NAH
        # when
        yeah = value_yeah.to_entity()
        nah = value_nah.to_entity()
        # then
        self.assertEqual(yeah, VoteValue.YEAH)
        self.assertEqual(nah, VoteValue.NAH)

    def test_vote_from_entity_should_convert_all_fields_when_called_with_valid_data(self):
        # given
        entity = Vote(user_id="u1", movie_id=42, vote=VoteValue.YEAH)
        # when
        actual = VoteDto.from_entity(entity)
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.movie_id, 42)
        self.assertEqual(actual.vote, VoteValueDto.YEAH)

    def test_vote_to_entity_should_convert_all_fields_when_called_with_valid_data(self):
        # given
        dto = VoteDto(user_id="u1", movie_id=42, vote=VoteValueDto.YEAH)
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.user_id, dto.user_id)
        self.assertEqual(actual.movie_id, dto.movie_id)
        self.assertEqual(actual.vote, VoteValue.YEAH)

    def test_vote_dto_from_entity_with_user_should_convert_all_fields_when_called_with_valid_data(self):
        # given
        user = User(user_id="u2", email="e@x", locale="en", nickname="Nick", profile_pic="/pic.png")
        users_by_id = {"u2": user}
        entity = Vote(user_id="u2", movie_id=99, vote=VoteValue.NAH)
        # when
        actual = VoteDto.from_entity_with_user(entity=entity, users=users_by_id)
        # then
        self.assertEqual(actual.user_id, "u2")
        self.assertEqual(actual.user_nickname, "Nick")
        self.assertEqual(actual.user_profile_pic, "/pic.png")
        self.assertEqual(actual.vote, VoteValueDto.NAH)

    def test_watch_history_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        entity = WatchHistory(user_id="u1", movie_id=7)
        # when
        actual = WatchHistoryDto.from_entity(entity)
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.movie_id, 7)

    def test_watch_history_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        dto = WatchHistoryDto(user_id="u1", movie_id=7)
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.movie_id, 7)

    def test_provider_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        entity = Provider(provider_id=10, name="Netflix", logo_path="/n.png")
        # when
        actual = ProviderDto.from_entity(entity)
        # then
        self.assertEqual(actual.provider_id, 10)
        self.assertEqual(actual.name, "Netflix")
        self.assertEqual(actual.logo_path, "/n.png")

    def test_provider_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        dto = ProviderDto(provider_id=10, name="Netflix", logo_path="/n.png")
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.provider_id, 10)
        self.assertEqual(actual.name, "Netflix")
        self.assertEqual(actual.logo_path, "/n.png")

    def test_provider_filter_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        entity = ProviderFilter(provider_id=22, location="US", priority=0)
        # when
        actual = ProviderFilterDto.from_entity(entity)
        # then
        self.assertEqual(actual.provider_id, 22)
        self.assertEqual(actual.location, "US")

    def test_provider_filter_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        dto = ProviderFilterDto(provider_id=22, location="US", priority=0)
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.provider_id, 22)
        self.assertEqual(actual.location, "US")

    def test_availability_type_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        # when
        stream = AvailabilityTypeDto.from_entity(AvailabilityType.STREAM)
        rent = AvailabilityTypeDto.from_entity(AvailabilityType.RENT)
        buy = AvailabilityTypeDto.from_entity(AvailabilityType.BUY)
        # then
        self.assertEqual(stream, AvailabilityTypeDto.STREAM)
        self.assertEqual(rent, AvailabilityTypeDto.RENT)
        self.assertEqual(buy, AvailabilityTypeDto.BUY)

    def test_availability_type_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        # when
        stream = AvailabilityTypeDto.STREAM.to_entity()
        rent = AvailabilityTypeDto.RENT.to_entity()
        buy = AvailabilityTypeDto.BUY.to_entity()
        # then
        self.assertEqual(stream, AvailabilityType.STREAM)
        self.assertEqual(rent, AvailabilityType.RENT)
        self.assertEqual(buy, AvailabilityType.BUY)

    def test_availability_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        provider = Provider(provider_id=1, name="Disney+", logo_path="/d.png")
        entity = Availability(
            provider=provider, movie_id=5, location="US", watch_type=AvailabilityType.RENT
        )
        # when
        actual = AvailabilityDto.from_entity(entity)
        # then
        self.assertEqual(actual.movie_id, 5)
        self.assertEqual(actual.location, "US")
        self.assertEqual(actual.watch_type, AvailabilityTypeDto.RENT)
        self.assertIsInstance(actual.provider, ProviderDto)
        self.assertEqual(actual.provider.name, "Disney+")

    def test_availability_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        provider = ProviderDto(provider_id=1, name="Disney+", logo_path="/d.png")
        dto = AvailabilityDto(
            provider=provider, movie_id=5, location="US", watch_type=AvailabilityTypeDto.RENT
        )
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.movie_id, 5)
        self.assertEqual(actual.location, "US")
        self.assertEqual(actual.watch_type, AvailabilityType.RENT)
        self.assertIsInstance(actual.provider, Provider)
        self.assertEqual(actual.provider.name, "Disney+")

    def test_genre_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        entity = Genre(genre_id=12, name="Adventure")
        # when
        actual = GenreDto.from_entity(entity)
        # then
        self.assertEqual(actual.genre_id, 12)
        self.assertEqual(actual.name, "Adventure")

    def test_genre_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        dto = GenreDto(genre_id=12, name="Adventure")
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.genre_id, 12)
        self.assertEqual(actual.name, "Adventure")

    def test_movie_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        genres = [Genre(28, "Action"), Genre(12, "Adventure")]
        movie = Movie(
            movie_id=101,
            title="Sample",
            overview="A test movie",
            duration=123,
            poster_path="/p.png",
            genres=genres,
            official_trailer="https://t.trailer",
            original_language="en",
            release_date=date(2024, 3, 1),
            status="Released",
        )
        provider_stream = Provider(8, "Netflix", "/n.png")
        provider_buy = Provider(9, "Apple TV", "/a.png")
        availabilities = [
            Availability(provider_stream, movie_id=101, location="US", watch_type=AvailabilityType.STREAM),
            Availability(provider_buy, movie_id=101, location="US", watch_type=AvailabilityType.BUY),
        ]
        users = [
            User(user_id="u1", email="a@a", locale="en", nickname="Alice", profile_pic="/a.png"),
            User(user_id="u2", email="b@b", locale="en", nickname="Bob", profile_pic="/b.png"),
            User(user_id="u3", email="c@c", locale="en", nickname="Charlie", profile_pic="/c.png"),
        ]
        votes = [
            Vote(user_id="u2", movie_id=101, vote=VoteValue.YEAH),
            Vote(user_id="u3", movie_id=101, vote=VoteValue.NAH),
        ]
        watch_history = [
            WatchHistory(user_id="u1", movie_id=101),
            WatchHistory(user_id="u3", movie_id=101)
        ]

        # when
        actual = MovieDto.from_entity(
            movie=movie, availabilities=availabilities, votes=votes, users=users, current_user_id="u1", watch_history=watch_history
        )
        # then - scalar fields
        self.assertEqual(actual.movie_id, 101)
        self.assertEqual(actual.title, "Sample")
        self.assertEqual(actual.overview, "A test movie")
        self.assertEqual(actual.duration, 123)
        self.assertEqual(actual.poster_path, "/p.png")
        self.assertEqual(actual.official_trailer, "https://t.trailer")
        self.assertEqual(actual.original_language, "en")
        self.assertEqual(actual.release_date, date(2024, 3, 1))
        self.assertEqual(actual.status, "Released")
        # then - genres
        self.assertEqual([g.genre_id for g in actual.genres], [28, 12])
        self.assertEqual([g.name for g in actual.genres], ["Action", "Adventure"])
        # then - providers
        self.assertEqual(len(actual.providers["stream"]), 1)
        self.assertIsInstance(actual.providers["stream"][0], AvailabilityDto)
        self.assertEqual(actual.providers["stream"][0].provider.name, "Netflix")
        self.assertEqual(actual.providers["stream"][0].watch_type, AvailabilityTypeDto.STREAM)
        self.assertEqual(len(actual.providers["buy_or_rent"]), 1)
        self.assertEqual(actual.providers["buy_or_rent"][0].provider.name, "Apple TV")
        self.assertEqual(actual.providers["buy_or_rent"][0].watch_type, AvailabilityTypeDto.BUY)
        # then - votes
        self.assertEqual(actual.votes["primary_vote"], None)
        liked = actual.votes["liked"]
        blocked = actual.votes["blocked"]
        self.assertEqual(len(liked), 1)
        self.assertEqual(liked[0].user_id, "u2")
        self.assertEqual(liked[0].vote, VoteValueDto.YEAH)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].user_id, "u3")
        self.assertEqual(blocked[0].vote, VoteValueDto.NAH)
        # then - watch history
        self.assertEqual(actual.watched, True)

    def test_movie_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        genres = [GenreDto(28, "Action"), GenreDto(12, "Adventure")]
        movie = MovieDto(
            movie_id=101,
            title="Sample",
            overview="A test movie",
            duration=123,
            poster_path="/p.png",
            genres=genres,
            official_trailer="https://t.trailer",
            original_language="en",
            release_date=date(2024, 3, 1),
            status="Released",
        )
        # when
        actual = movie.to_entity()
        # then - scalar fields
        self.assertEqual(actual.movie_id, 101)
        self.assertEqual(actual.title, "Sample")
        self.assertEqual(actual.overview, "A test movie")
        self.assertEqual(actual.duration, 123)
        self.assertEqual(actual.poster_path, "/p.png")
        self.assertEqual(actual.official_trailer, "https://t.trailer")
        self.assertEqual(actual.original_language, "en")
        self.assertEqual(actual.release_date, date(2024, 3, 1))
        self.assertEqual(actual.status, "Released")
        # then - genres
        self.assertEqual([g.genre_id for g in actual.genres], [28, 12])
        self.assertEqual([g.name for g in actual.genres], ["Action", "Adventure"])

    def test_tmdb_user_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        entity = TmdbUser(
            user_id="u1",
            tmdb_id=1234,
            session="sess",
            include_adult=False,
            iso_3166_1="US",
            iso_639_1="en",
            username="tmdb_user",
            name="TMDB Name",
        )
        # when 
        actual = TmdbUserDto.from_entity(entity)
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.tmdb_id, 1234)
        self.assertEqual(actual.session, "sess")
        self.assertFalse(actual.include_adult)
        self.assertEqual(actual.iso_3166_1, "US")
        self.assertEqual(actual.iso_639_1, "en")
        self.assertEqual(actual.username, "tmdb_user")
        self.assertEqual(actual.name, "TMDB Name")

    def test_tmdb_user_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        dto = TmdbUserDto(
            user_id="u1",
            tmdb_id=1234,
            session="sess",
            include_adult=False,
            iso_3166_1="US",
            iso_639_1="en",
            username="tmdb_user",
            name="TMDB Name",
        )
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.tmdb_id, 1234)
        self.assertEqual(actual.session, "sess")
        self.assertFalse(actual.include_adult)
        self.assertEqual(actual.iso_3166_1, "US")
        self.assertEqual(actual.iso_639_1, "en")
        self.assertEqual(actual.username, "tmdb_user")
        self.assertEqual(actual.name, "TMDB Name")

    def test_user_from_entity_with_tmdb_should_convert_value_when_called_with_valid_data(self):
        # given
        user = User(user_id="u1", email="e@x", locale="en", nickname="Neo", profile_pic="/neo.png")
        tmdb = TmdbUser(
            user_id="u1",
            tmdb_id=1,
            session="s",
            include_adult=True,
            iso_3166_1="US",
            iso_639_1="en",
            username="neo",
            name="Neo",
        )
        # when
        actual = UserDto.from_entity(entity=user, tmdb_user=tmdb)
        # then
        self.assertEqual(actual.user_id, "u1")
        self.assertEqual(actual.email, "e@x")
        self.assertEqual(actual.locale, "en")
        self.assertEqual(actual.nickname, "Neo")
        self.assertEqual(actual.profile_pic, "/neo.png")
        self.assertIsNotNone(actual.tmdb_user)
        self.assertEqual(actual.tmdb_user.username, "neo")

    def test_user_to_entity_with_tmdb_should_convert_value_when_called_with_valid_data(self):
        # given
        tmdb = TmdbUserDto(
            user_id="u1",
            tmdb_id=1,
            session="s",
            include_adult=True,
            iso_3166_1="US",
            iso_639_1="en",
            username="neo",
            name="Neo",
        )
        user = UserDto(user_id="u1", email="e@x", locale="en", nickname="Neo", profile_pic="/neo.png", tmdb_user=tmdb)
        # when
        actual_user = user.to_entity()
        # then
        self.assertEqual(actual_user.user_id, "u1")
        self.assertEqual(actual_user.email, "e@x")
        self.assertEqual(actual_user.locale, "en")
        self.assertEqual(actual_user.nickname, "Neo")
        self.assertEqual(actual_user.profile_pic, "/neo.png")

    def test_user_from_entity_without_tmdb_should_convert_value_when_called_with_valid_data(self):
        # given
        user = User(user_id="u1", email="e@x", locale="en", nickname="Neo", profile_pic="/neo.png")
        # when
        actual = UserDto.from_entity(entity=user, tmdb_user=None)
        # then
        self.assertIsNone(actual.tmdb_user)

    def test_watchlist_from_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        wl_id = uuid4()
        provider_filters = [
            ProviderFilter(provider_id=8, location="US", priority=0),
            ProviderFilter(provider_id=9, location="DE", priority=0)
        ]
        users = [
            User(user_id="u1", email="a@a", locale="en", nickname="Alice", profile_pic="/a.png"),
            User(user_id="u2", email="b@b", locale="en", nickname="Bob", profile_pic="/b.png"),
        ]
        entity = WatchList(watchlist_id=wl_id, name="WL", provider_filters=provider_filters, users=users)
        # when
        actual = WatchListDto.from_entity(entity)
        # then
        self.assertEqual(actual.watchlist_id, wl_id)
        self.assertEqual(actual.name, "WL")
        self.assertEqual(len(actual.provider_filters), 2)

    def test_watchlist_to_entity_should_convert_value_when_called_with_valid_data(self):
        # given
        wl_id = uuid4()
        provider_filters = [
            ProviderFilterDto(provider_id=8, location="US", priority=0),
            ProviderFilterDto(provider_id=9, location="DE", priority=0)
        ]
        users = [
            UserDto(user_id="u1", email="a@a", locale="en", nickname="Alice", profile_pic="/a.png"),
            UserDto(user_id="u2", email="b@b", locale="en", nickname="Bob", profile_pic="/b.png"),
        ]
        dto = WatchListDto(watchlist_id=wl_id, name="WL", provider_filters=provider_filters, users=users)
        # when
        actual = dto.to_entity()
        # then
        self.assertEqual(actual.watchlist_id, wl_id)
        self.assertEqual(actual.name, "WL")
        self.assertEqual(len(actual.provider_filters), 2)
