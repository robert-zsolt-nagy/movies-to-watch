from unittest.mock import MagicMock

from src.dao.m2w_graph_db_entities import VoteValue
from src.dao.m2w_graph_db_repository_users import save_or_update_user
from src.dao.m2w_graph_db_repository_votes_and_watch_status import get_all_votes_of_watchlist, \
    get_all_watch_history_of_watchlist
from src.dao.m2w_graph_db_repository_watchlists import add_user_to_watchlist
from src.dao.secret_manager import SecretManager
from src.services.group_service import GroupManagerService
from src.services.m2w_dtos import VoteValueDto
from src.services.user_service import UserManagerService
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase, get_john_doe


class TestGroupManagerService(M2wDatabaseTestCase):

    def test_like_movie_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            db=self.driver,
            user_service=MagicMock(UserManagerService)
        )
        under_test.user.add_movie_to_users_watchlist = MagicMock(return_value=True)
        # when
        response = under_test.vote_for_movie_by_user(user_id=self.user_id, movie_id=self.movie_id, vote=VoteValueDto.YEAH)
        # then
        self.assertEqual(response, True)
        under_test.user.add_movie_to_users_watchlist.assert_called_with(movie_id=self.movie_id, user_id=self.user_id)
        tx = self.session.begin_transaction()
        votes = get_all_votes_of_watchlist(tx=tx, user_ids=[self.user_id], movie_ids=[self.movie_id])
        tx.commit()
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0].user_id, self.user_id)
        self.assertEqual(votes[0].movie_id, self.movie_id)
        self.assertEqual(votes[0].vote, VoteValue.YEAH)

    def test_block_movie_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            db=self.driver,
            user_service=MagicMock(UserManagerService)
        )
        under_test.user.remove_movie_from_users_watchlist = MagicMock(return_value=True)
        # when
        response = under_test.vote_for_movie_by_user(user_id=self.user_id, movie_id=self.movie_id, vote=VoteValueDto.NAH)
        # then
        self.assertEqual(response, True)
        under_test.user.remove_movie_from_users_watchlist.assert_called_with(movie_id=self.movie_id, user_id=self.user_id)
        tx = self.session.begin_transaction()
        votes = get_all_votes_of_watchlist(tx=tx, user_ids=[self.user_id], movie_ids=[self.movie_id])
        tx.commit()
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0].user_id, self.user_id)
        self.assertEqual(votes[0].movie_id, self.movie_id)
        self.assertEqual(votes[0].vote, VoteValue.NAH)

    def test_watch_movie_by_user_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            db=self.driver,
            user_service=MagicMock(UserManagerService)
        )
        under_test.user.remove_movie_from_users_watchlist = MagicMock(return_value=True)
        # when
        response = under_test.watch_movie_by_user(user_id=self.user_id, movie_id=self.movie_id)
        # then
        self.assertEqual(response, True)
        under_test.user.remove_movie_from_users_watchlist.assert_called_with(movie_id=self.movie_id, user_id=self.user_id)
        tx = self.session.begin_transaction()
        history = get_all_watch_history_of_watchlist(tx=tx, user_ids=[self.user_id], movie_ids=[self.movie_id])
        tx.commit()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].user_id, self.user_id)
        self.assertEqual(history[0].movie_id, self.movie_id)

    def test_watch_movie_by_group_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        john = get_john_doe()
        tx = self.session.begin_transaction()
        save_or_update_user(tx=tx, user=john)
        add_user_to_watchlist(tx=tx, user_id=john.user_id, watchlist_id=self.watchlist_id, primary=True)
        tx.commit()
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            db=self.driver,
            user_service=MagicMock(UserManagerService)
        )
        under_test.user.remove_movie_from_users_watchlist = MagicMock(return_value=True)
        # when
        response = under_test.watch_movie_by_group(user_id=self.user_id, movie_id=self.movie_id, group_id=self.watchlist_id)
        # then
        self.assertEqual(response, True)
        call_count = len(under_test.user.remove_movie_from_users_watchlist.call_args_list)
        self.assertEqual(call_count, 2)
        tx = self.session.begin_transaction()
        history = get_all_watch_history_of_watchlist(tx=tx, user_ids=[self.user_id, john.user_id], movie_ids=[self.movie_id])
        tx.commit()
        self.assertEqual(len(history), 2)
        for h in history:
            self.assertIn(h.user_id, [self.user_id, john.user_id])
            self.assertIn(h.movie_id, [self.movie_id])

    def test_get_primary_group_for_m2w_user_should_pass_correct_parameters(self):
        # given
        self.insert_default_user_and_movie()
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            db=self.driver,
            user_service=MagicMock(UserManagerService)
        )
        # when
        response = under_test.get_primary_group_for_m2w_user(user_id=self.user_id)
        # then
        self.assertEqual(response.watchlist_id, self.watchlist_id)


