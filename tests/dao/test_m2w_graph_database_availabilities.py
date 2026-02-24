from src.dao.m2w_graph_db_entities import Provider, Availability, AvailabilityType, \
    ProviderFilter
from src.dao.m2w_graph_db_repository_availabilities import save_movie_availabilities, \
    get_all_availabilities_for_movies
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase


class TestM2wGraphDatabaseAvailabilities(M2wDatabaseTestCase):

    def test_save_movie_availabilities_should_save_all_entries_when_the_movie_is_available_from_multiple_providers(self):
        # given
        self.insert_default_user_and_movie()
        to_save = [
            Availability(
                movie_id=self.movie_id,
                provider=Provider(2, "HBO Max", "hbo-logo.png"),
                location="HU",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="DE",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="GB",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="HU",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(3, "Youtube", "youtube-logo.png"),
                location="HU",
                watch_type=AvailabilityType.BUY
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(3, "Youtube", "youtube-logo.png"),
                location="HU",
                watch_type=AvailabilityType.RENT
            )
        ]
        # when
        tx = self.session.begin_transaction()
        save_movie_availabilities(tx=tx, movie_id=self.movie_id, availabilities=to_save)
        tx.commit()
        # then
        tx = self.session.begin_transaction()
        actual = get_all_availabilities_for_movies(tx=tx, movie_ids=[self.movie_id])
        self.assert_provider_count_is(tx, 3)
        tx.commit()
        self.assert_availability_list_equals(actual, to_save)

    def test_save_movie_availabilities_should_delete_all_previous_entries_when_the_movie_is_not_available(self):
        # given
        self.insert_default_user_and_movie()
        to_save = [
            Availability(
                movie_id=self.movie_id,
                provider=Provider(2, "HBO Max", "hbo-logo.png"),
                location="HU",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="DE",
                watch_type=AvailabilityType.STREAM
            )
        ]
        tx = self.session.begin_transaction()
        save_movie_availabilities(tx=tx, movie_id=self.movie_id, availabilities=to_save)
        tx.commit()
        to_save = []
        # when
        tx = self.session.begin_transaction()
        save_movie_availabilities(tx=tx, movie_id=self.movie_id, availabilities=to_save)
        tx.commit()
        # then
        tx = self.session.begin_transaction()
        actual = get_all_availabilities_for_movies(tx=tx, movie_ids=[self.movie_id])
        self.assert_provider_count_is(tx, 2)
        tx.commit()
        self.assert_availability_list_equals(actual, to_save)

    def test_get_all_availabilities_for_movies_should_filter_by_movie_ids_providers_and_locations_when_specified(self):
        # given
        self.insert_default_user_and_movie()
        second_movie = self.movie_id + 1
        self.insert_movie(movie_id=second_movie)
        to_save_first = [
            Availability(
                movie_id=self.movie_id,
                provider=Provider(2, "HBO Max", "hbo-logo.png"),
                location="HU",
                watch_type=AvailabilityType.STREAM
            ),
            Availability(
                movie_id=self.movie_id,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="DE",
                watch_type=AvailabilityType.STREAM
            )
        ]
        to_save_second = [
            Availability(
                movie_id=second_movie,
                provider=Provider(3, "Youtube", "youtube-logo.png"),
                location="HU",
                watch_type=AvailabilityType.RENT
            ),
            Availability(
                movie_id=second_movie,
                provider=Provider(1, "Netflix", "netflix-logo.png"),
                location="HU",
                watch_type=AvailabilityType.STREAM
            )
        ]
        tx = self.session.begin_transaction()
        save_movie_availabilities(tx=tx, movie_id=self.movie_id, availabilities=to_save_first)
        save_movie_availabilities(tx=tx, movie_id=second_movie, availabilities=to_save_second)
        tx.commit()
        expected = [to_save_first[0]]
        # when
        tx = self.session.begin_transaction()
        actual = get_all_availabilities_for_movies(tx=tx, movie_ids=[self.movie_id], provider_filters=[
            ProviderFilter(provider_id=1,location="HU", priority=0),
            ProviderFilter(provider_id=2,location="HU", priority=0),
        ])
        # then
        self.assert_provider_count_is(tx, 3)
        tx.commit()
        self.assert_availability_list_equals(actual, expected)

