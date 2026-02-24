import uuid
from datetime import datetime

from src.dao.m2w_graph_db_entities import VoteValue, M2WDatabaseException
from src.dao.m2w_graph_db_repository_votes_and_watch_status import vote_for_movie
from tests.dao.test_m2w_graph_database import M2wDatabaseTestCase


class TestM2wGraphDatabaseVotes(M2wDatabaseTestCase):

    def test_vote_for_movie_should_raise_exception_when_movie_not_found(self):
        # given
        self.insert_default_user_and_movie()
        # when
        tx = self.session.begin_transaction()
        try:
            vote_for_movie(tx=tx, user_id=self.user_id, movie_id=self.movie_id + 1, vote_value=VoteValue.YEAH)
            self.fail("should have thrown exception")
        # then
        except Exception as e:
            self.assertIsInstance(e, M2WDatabaseException)
            tx.rollback()

    def test_vote_for_movie_should_raise_exception_when_user_not_found(self):
        # given
        self.insert_default_user_and_movie()
        # when
        tx = self.session.begin_transaction()
        try:
            vote_for_movie(tx=tx, user_id=uuid.uuid4().hex, movie_id=self.movie_id, vote_value=VoteValue.YEAH)
            self.fail("should have thrown exception")
        # then
        except Exception as e:
            self.assertIsInstance(e, M2WDatabaseException)
            tx.rollback()

    def test_vote_for_movie_should_save_vote_when_no_previous_vote_exists(self):
        # given
        self.insert_default_user_and_movie()
        # when
        tx = self.session.begin_transaction()
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=self.movie_id, vote_value=VoteValue.YEAH)
        tx.commit()
        # then
        actual = self.find_single_vote()
        self.assertEqual(actual.vote, VoteValue.YEAH)
        self.assertIsNotNone(actual.updated_at)

    def test_vote_for_movie_should_overwrite_previous_vote_when_exists(self):
        # given
        self.insert_default_user_and_movie()
        tx = self.session.begin_transaction()
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=self.movie_id, vote_value=VoteValue.YEAH)
        tx.commit()
        before = datetime.now()
        # when
        tx = self.session.begin_transaction()
        vote_for_movie(tx=tx, user_id=self.user_id, movie_id=self.movie_id, vote_value=VoteValue.NAH)
        tx.commit()
        # then
        after = datetime.now()
        actual = self.find_single_vote()
        self.assertEqual(actual.vote, VoteValue.NAH)
        self.assertGreaterEqual(actual.updated_at, before)
        self.assertLessEqual(actual.updated_at, after)

