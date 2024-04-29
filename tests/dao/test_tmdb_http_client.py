from unittest import TestCase
from unittest.mock import MagicMock

import requests
from src.dao.tmdb_http_client import TmdbHttpClient, TmdbHttpClientException

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

    def test_post_should_merge_all_headers_when_called_with_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "status_code": 1,
            "status_message": "Success."
        })
        response.status_code = 200

        session = requests.Session()
        session.post = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)
        payload = {
            "success": True,
            "expires_at": "2016-08-26 17:04:39 UTC",
            "request_token": "new_token"
        }

        # when
        result = under_test.post(path="/path", content_type="application/json", payload=payload, additional_headers={"X-Request-ID": "1"}, params={"param1":1})

        # then
        self.assertEqual(result, {
            "status_code": 1,
            "status_message": "Success."
        })
        session.post.assert_called_with(url="http://example.com/path", json=payload, params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore",
            "Content-Type":"application/json",
            "X-Request-ID": "1"
        })

    def test_post_should_use_default_headers_when_called_without_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "status_code": 1,
            "status_message": "Success."
        })
        response.status_code = 200

        session = requests.Session()
        session.post = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)
        payload = {
            "success": True,
            "expires_at": "2016-08-26 17:04:39 UTC",
            "request_token": "new_token"
        }

        # when
        result = under_test.post(path="/path", content_type="application/json", payload=payload, params={"param1":1})

        # then
        self.assertEqual(result, {
            "status_code": 1,
            "status_message": "Success."
        })
        session.post.assert_called_with(url="http://example.com/path", json=payload, params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore",
            "Content-Type":"application/json"
        })

    def test_delete_should_merge_all_headers_when_called_with_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "status_code": 1,
            "status_message": "The item/record was updated successfully."
        })
        response.status_code = 200

        session = requests.Session()
        session.delete = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)

        # when
        result = under_test.delete(path="/path", params={"param1":1}, additional_headers={"X-Request-ID": "1"})

        # then
        self.assertEqual(result, {
            "status_code": 1,
            "status_message": "The item/record was updated successfully."
        })
        session.delete.assert_called_with(url="http://example.com/path", params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore",
            "X-Request-ID": "1"
        })

    def test_delete_should_use_default_headers_when_called_without_additional_headers(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "status_code": 1,
            "status_message": "The item/record was updated successfully."
        })
        response.status_code = 200

        session = requests.Session()
        session.delete = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)

        # when
        result = under_test.delete(path="/path", params={"param1":1})

        # then
        self.assertEqual(result, {
            "status_code": 1,
            "status_message": "The item/record was updated successfully."
        })
        session.delete.assert_called_with(url="http://example.com/path", params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore"
        })

    def test_get_should_raise_exception_if_response_satus_code_is_unexpected(self):
        # given
        response = requests.Response()
        response.json = MagicMock(return_value={
            "success": True
        })
        response.status_code = 404

        session = requests.Session()
        session.get = MagicMock(return_value=response)

        under_test = TmdbHttpClient(token="ignore", base_url="http://example.com", session=session)

        # when
        self.assertRaises(TmdbHttpClientException, lambda: under_test.get(path="/path", params={"param1":1}, additional_headers={"X-Request-ID": "1"}))

        # then
        session.get.assert_called_with(url="http://example.com/path", params={"param1":1}, headers={
            "accept": "application/json",
            "Authorization": "Bearer ignore",
            "X-Request-ID": "1"
        })