from unittest import TestCase
from unittest.mock import MagicMock, Mock

import requests
from src.dao.tmdb_http_client import TmdbHttpClient

class TestTmdbHttpClient(TestCase):
    def test_get_should_merge_all_headers_when_called_with_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "success": True
        })
        response.status_code = 200

        session = requests.Session()
        session.get = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)

        # when
        result = under_test.get(path="/path", params={"param1":1}, additional_headers={"X-Request-ID": "1"})

        # then
        self.assertEqual(result, {
            "success": True
        })
        session.get.assert_called_with(url="http://example.com/path", params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore",
            "X-Request-ID": "1"
        })

    def test_get_should_use_default_headers_when_called_without_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "success": True
        })
        response.status_code = 200

        session = requests.Session()
        session.get = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)

        # when
        result = under_test.get(path="/path", params={"param1":1})

        # then
        self.assertEqual(result, {
            "success": True
        })
        session.get.assert_called_with(url="http://example.com/path", params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore"
        })