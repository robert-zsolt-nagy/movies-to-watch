import uuid
from asyncio import wait_for
from datetime import timedelta, datetime
from time import sleep

from src.dao.m2w_graph_db_entities import M2WDatabaseException, WatchList, Provider, ProviderFilter
from src.dao.m2w_graph_db_repository_availabilities import save_or_update_provider
from src.dao.m2w_graph_db_repository_users import save_or_update_user
from src.dao.m2w_graph_db_repository_watchlists import add_user_to_watchlist, save_or_update_watchlist, \
    get_watchlist_details, get_primary_watchlist_id, get_all_provider_filters
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase, get_john_doe


class TestM2wGraphDatabaseVotes(M2wDatabaseTestCase):

    def test_add_user_to_watchlist_should_raise_exception_when_watchlist_not_found(self):
        # given
        watchlist = WatchList(watchlist_id=uuid.uuid4(), name="Test list", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=user)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        try:
            add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist.watchlist_id)
            self.fail("should have thrown exception")
        # then
        except Exception as e:
            self.assertIsInstance(e, M2WDatabaseException)
            tx.rollback()

    def test_add_user_to_watchlist_should_raise_exception_when_user_not_found(self):
        # given
        watchlist = WatchList(watchlist_id=uuid.uuid4(), name="Test list", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_watchlist(tx=tx, watchlist=watchlist)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        try:
            add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist.watchlist_id)
            self.fail("should have thrown exception")
        # then
        except Exception as e:
            self.assertIsInstance(e, M2WDatabaseException)
            tx.rollback()

    def test_add_user_to_watchlist_should_save_member_when_both_entities_are_found(self):
        # given
        watchlist = WatchList(watchlist_id=uuid.uuid4(), name="Test list", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_watchlist(tx=tx, watchlist=watchlist)
        save_or_update_user(tx=tx, user=user)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist.watchlist_id)
        tx.commit()
        # then
        tx = self.session.begin_transaction()
        actual = get_watchlist_details(tx=tx, watchlist_id=watchlist.watchlist_id)
        tx.commit()
        self.assertIsNotNone(actual.updated_at)
        self.assertEqual(actual.watchlist_id, watchlist.watchlist_id)
        self.assertEqual(actual.name, watchlist.name)
        self.assertEqual(len(actual.users), 1)
        self.assert_user_equals(actual.users[0], user)

    def test_add_user_to_watchlist_should_not_mark_relation_as_primary_when_called_with_false(self):
        # given
        watchlist_1 = WatchList(watchlist_id=uuid.uuid4(), name="1", provider_filters=[])
        watchlist_2 = WatchList(watchlist_id=uuid.uuid4(), name="2", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_watchlist(tx=tx, watchlist=watchlist_1)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_2)
        save_or_update_user(tx=tx, user=user)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_1.watchlist_id, primary=True)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_2.watchlist_id, primary=False)
        tx.commit()
        # then
        tx = self.session.begin_transaction()
        actual = get_primary_watchlist_id(tx=tx, user_id=user.user_id)
        tx.commit()
        self.assertEqual(actual, watchlist_1.watchlist_id)

    def test_add_user_to_watchlist_should_allow_maximum_one_primary_relation_when_called_with_true(self):
        # given
        watchlist_1 = WatchList(watchlist_id=uuid.uuid4(), name="1", provider_filters=[])
        watchlist_2 = WatchList(watchlist_id=uuid.uuid4(), name="2", provider_filters=[])
        watchlist_3 = WatchList(watchlist_id=uuid.uuid4(), name="3", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_watchlist(tx=tx, watchlist=watchlist_1)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_2)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_3)
        save_or_update_user(tx=tx, user=user)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_1.watchlist_id, primary=True)
        sleep(0.1)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_2.watchlist_id, primary=True)
        sleep(0.1)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_3.watchlist_id, primary=True)
        tx.commit()
        # then
        tx = self.session.begin_transaction()
        actual = get_primary_watchlist_id(tx=tx, user_id=user.user_id)
        tx.commit()
        self.assertEqual(actual, watchlist_1.watchlist_id)

    def test_get_primary_watchlist_id_should_return_oldest_list_when_none_are_primary(self):
        # given
        watchlist_1 = WatchList(watchlist_id=uuid.uuid4(), name="1", provider_filters=[])
        watchlist_2 = WatchList(watchlist_id=uuid.uuid4(), name="2", provider_filters=[])
        watchlist_3 = WatchList(watchlist_id=uuid.uuid4(), name="3", provider_filters=[])
        user = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=user)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_2)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_2.watchlist_id, primary=False)
        sleep(0.1)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_1)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_1.watchlist_id, primary=False)
        sleep(0.1)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_3)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_3.watchlist_id, primary=False)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = get_primary_watchlist_id(tx=tx, user_id=user.user_id)
        tx.commit()
        # then
        self.assertEqual(actual, watchlist_2.watchlist_id)

    def test_get_watchlist_details_should_return_the_list_of_included_providers_when_present(self):
        # given
        watchlist = WatchList(watchlist_id=uuid.uuid4(), name="Test list", provider_filters=[
            ProviderFilter(provider_id=1, location="HU", priority=0),
            ProviderFilter(provider_id=1, location="DE", priority=1),
            ProviderFilter(provider_id=2, location="HU", priority=0),
        ])
        user = get_john_doe()
        provider_1 = Provider(provider_id=1, name="provider 1", logo_path="provider-1-logo.png")
        provider_2 = Provider(provider_id=2, name="provider 2", logo_path="provider-2-logo.png")
        unrelated_provider = Provider(provider_id=3, name="provider 3", logo_path="provider-3-logo.png")
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=user)
        save_or_update_provider(tx=tx, provider=provider_1)
        save_or_update_provider(tx=tx, provider=provider_2)
        save_or_update_provider(tx=tx, provider=unrelated_provider)
        save_or_update_watchlist(tx=tx, watchlist=watchlist)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist.watchlist_id)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = get_watchlist_details(tx=tx, watchlist_id=watchlist.watchlist_id)
        tx.commit()
        # then
        self.assertEqual(actual.watchlist_id, watchlist.watchlist_id)
        self.assertEqual(actual.name, watchlist.name)
        self.assertEqual(len(actual.users), 1)
        self.assert_user_equals(actual.users[0], user)
        self.assertEqual(len(actual.provider_filters), 3)
        self.assertEqual(actual.provider_filters[0].provider_id, provider_1.provider_id)
        self.assertEqual(actual.provider_filters[0].location, "HU")
        self.assertEqual(actual.provider_filters[0].priority, 0)
        self.assertEqual(actual.provider_filters[1].provider_id, provider_1.provider_id)
        self.assertEqual(actual.provider_filters[1].location, "DE")
        self.assertEqual(actual.provider_filters[1].priority, 1)
        self.assertEqual(actual.provider_filters[2].provider_id, provider_2.provider_id)
        self.assertEqual(actual.provider_filters[2].location, "HU")
        self.assertEqual(actual.provider_filters[2].priority, 0)

    def test_get_all_provider_filters_should_return_the_list_of_all_providers_when_called(self):
        # given
        watchlist_1 = WatchList(watchlist_id=uuid.uuid4(), name="Test list 1", provider_filters=[
            ProviderFilter(provider_id=1, location="HU", priority=0),
            ProviderFilter(provider_id=1, location="DE", priority=1),
            ProviderFilter(provider_id=2, location="HU", priority=0),
        ])
        watchlist_2 = WatchList(watchlist_id=uuid.uuid4(), name="Test list 2", provider_filters=[
            ProviderFilter(provider_id=1, location="HU", priority=0),
            ProviderFilter(provider_id=2, location="DE", priority=1),
            ProviderFilter(provider_id=3, location="HU", priority=0),
        ])
        user = get_john_doe()
        provider_1 = Provider(provider_id=1, name="provider 1", logo_path="provider-1-logo.png")
        provider_2 = Provider(provider_id=2, name="provider 2", logo_path="provider-2-logo.png")
        provider_3 = Provider(provider_id=3, name="provider 3", logo_path="provider-3-logo.png")
        unrelated_provider = Provider(provider_id=4, name="provider 4", logo_path="provider-4-logo.png")
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=user)
        save_or_update_provider(tx=tx, provider=provider_1)
        save_or_update_provider(tx=tx, provider=provider_2)
        save_or_update_provider(tx=tx, provider=provider_3)
        save_or_update_provider(tx=tx, provider=unrelated_provider)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_1)
        save_or_update_watchlist(tx=tx, watchlist=watchlist_2)
        add_user_to_watchlist(tx=tx, user_id=user.user_id, watchlist_id=watchlist_1.watchlist_id)
        tx.commit()
        # when
        tx = self.session.begin_transaction()
        actual = get_all_provider_filters(tx=tx)
        tx.commit()
        # then
        self.assertEqual(len(actual), 5)
        self.assertEqual(actual[0].provider_id, provider_1.provider_id)
        self.assertEqual(actual[0].location, "HU")
        self.assertEqual(actual[0].priority, 0)
        self.assertEqual(actual[1].provider_id, provider_1.provider_id)
        self.assertEqual(actual[1].location, "DE")
        self.assertEqual(actual[1].priority, 1)
        self.assertEqual(actual[2].provider_id, provider_2.provider_id)
        self.assertEqual(actual[2].location, "HU")
        self.assertEqual(actual[2].priority, 0)
        self.assertEqual(actual[3].provider_id, provider_2.provider_id)
        self.assertEqual(actual[3].location, "DE")
        self.assertEqual(actual[3].priority, 1)
        self.assertEqual(actual[4].provider_id, provider_3.provider_id)
        self.assertEqual(actual[4].location, "HU")
        self.assertEqual(actual[4].priority, 0)
