import uuid
from datetime import date
from unittest import TestCase

from neo4j import Transaction
from testcontainers.neo4j import Neo4jContainer

from src.dao.m2w_graph_db_entities import TmdbUser, Movie, Availability, User, Vote, Genre
from src.dao.m2w_graph_db_repository_movies import get_one_movie_by_id
from src.dao.m2w_graph_db_repository_users import get_one_user, get_one_tmdb_user, save_or_update_tmdb_user
from src.dao.m2w_graph_db_repository_votes_and_watch_status import get_all_votes_of_watchlist


def get_the_matrix_movie() -> Movie:
    return Movie(
        movie_id=42,
        title="The Matrix",
        overview="Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.",
        duration=136,
        poster_path="https://example.com/poster.jpg",
        genres=[
            Genre(3, "Action"),
            Genre(4, "Science Fiction")
        ],
        official_trailer="https://example.com/trailer",
        original_language="en",
        release_date=date(year=1999, month=5, day=8),
        status="RELEASED"
    )

def get_john_doe() -> User:
    return User(
        user_id=uuid.uuid4().hex,
        email="johndoe@example.com",
        locale="HU",
        nickname="johndoe",
        profile_pic="10.png"
    )


class M2wDatabaseTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.neo4j_container = Neo4jContainer()
        cls.neo4j_container.start()

    @classmethod
    def tearDownClass(cls):
        cls.neo4j_container.stop()

    def setUp(self):
        self.driver = self.neo4j_container.get_driver()
        self.session = self.driver.session()

    def tearDown(self):
        self.session.run(
            query="""
                MATCH (n)
                DETACH DELETE n
            """)
        self.session.close()

    def find_single_user(self, user_id: str):
        tx = self.session.begin_transaction()
        result = get_one_user(tx=tx, user_id=user_id)
        tx.commit()
        return result

    def find_single_tmdb_user(self, user_id: str):
        tx = self.session.begin_transaction()
        result = get_one_tmdb_user(tx=tx, user_id=user_id)
        tx.commit()
        return result

    def find_single_movie(self, movie_id: int):
        tx = self.session.begin_transaction()
        result = get_one_movie_by_id(tx=tx, movie_id=movie_id)
        tx.commit()
        return result

    def insert_default_user_and_movie(self):
        self.watchlist_id = uuid.uuid4()
        self.user_id = uuid.uuid4().hex
        self.movie_id = 1
        self.session.run(
            query="""
                MERGE (:Watchlist {id: $watchlist_id})-[:MEMBER]->(:User {id: $user_id})
                MERGE (:Movie {id: $movie_id})
            """,
            parameters={
                "watchlist_id": self.watchlist_id.hex,
                "user_id": self.user_id,
                "movie_id": self.movie_id
            },
        )

    def insert_tmdb_user_travis_bell(self):
        tx = self.session.begin_transaction()
        save_or_update_tmdb_user(tx=tx, user=TmdbUser(
            user_id=self.user_id,
            tmdb_id=548,
            session="session",
            include_adult=True,
            iso_3166_1="CA",
            iso_639_1="en",
            name="Travis Bell",
            username="travisbell"
        ))
        tx.commit()

    def insert_movie(self, movie_id: int):
        self.session.run(
            query="""
                MERGE (:Movie {id: $movie_id})
            """,
            parameters={
                "movie_id": movie_id
            },
        )

    def find_single_vote(self) -> Vote:
        tx = self.session.begin_transaction()
        results = get_all_votes_of_watchlist(tx=tx, movie_ids=[self.movie_id], user_ids=[self.user_id])
        tx.commit()
        if len(results) != 1:
            self.fail("Unable to find vote")
        return results.pop(0)

    def assert_genre_equals(self, actual, expected):
        self.assertEqual(actual.genre_id, expected.genre_id)
        self.assertEqual(actual.name, expected.name)

    def assert_provider_count_is(self, tx: Transaction, expected: int):
        provider_count = tx.run(
            query="""
                MATCH (:Provider)
                RETURN count(*) AS count
            """
        ).single().get("count")
        self.assertEqual(provider_count, expected)

    def assert_user_equals(self, actual: User, expected: User):
        self.assertEqual(actual.user_id, expected.user_id)
        self.assertEqual(actual.email, expected.email)
        self.assertEqual(actual.locale, expected.locale)
        self.assertEqual(actual.nickname, expected.nickname)
        self.assertEqual(actual.profile_pic, expected.profile_pic)
        self.assertEqual(actual.updated_at, expected.updated_at)

    def assert_tmdb_user_equals(self, actual: TmdbUser, expected: TmdbUser):
        self.assertEqual(actual.user_id, expected.user_id)
        self.assertEqual(actual.tmdb_id, expected.tmdb_id)
        self.assertEqual(actual.session, expected.session)
        self.assertEqual(actual.username, expected.username)
        self.assertEqual(actual.include_adult, expected.include_adult)
        self.assertEqual(actual.iso_639_1, expected.iso_639_1)
        self.assertEqual(actual.iso_3166_1, expected.iso_3166_1)
        self.assertEqual(actual.updated_at, expected.updated_at)

    def assert_movie_equals(self, actual: Movie, expected: Movie):
        self.assertEqual(actual.movie_id, expected.movie_id)
        self.assertEqual(actual.title, expected.title)
        self.assertEqual(actual.overview, expected.overview)
        self.assertEqual(actual.duration, expected.duration)
        self.assertEqual(actual.poster_path, expected.poster_path)
        self.assertEqual(len(actual.genres), len(expected.genres))
        for i in range(len(actual.genres)):
            self.assert_genre_equals(actual.genres[i], expected.genres[i])
        self.assertEqual(actual.official_trailer, expected.official_trailer)
        self.assertEqual(actual.original_language, expected.original_language)
        self.assertEqual(actual.release_date, expected.release_date)
        self.assertEqual(actual.status, expected.status)
        self.assertEqual(actual.updated_at, expected.updated_at)

    def assert_availability_equals(self, actual: Availability, expected: Availability):
        self.assertEqual(actual.provider.provider_id, expected.provider.provider_id)
        self.assertEqual(actual.provider.name, expected.provider.name)
        self.assertEqual(actual.provider.logo_path, expected.provider.logo_path)
        self.assertEqual(actual.provider.updated_at, expected.provider.updated_at)
        self.assertEqual(actual.location, expected.location)
        self.assertEqual(actual.watch_type, expected.watch_type)
        self.assertEqual(actual.updated_at, expected.updated_at)

    def assert_availability_list_equals(self, actual: list[Availability], expected: list[Availability]):
        assert len(actual) == len(expected)
        for i in range(len(actual)):
            self.assert_availability_equals(actual[i], expected[i])
