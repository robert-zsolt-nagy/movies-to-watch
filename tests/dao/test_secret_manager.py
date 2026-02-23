from unittest import TestCase

from src.dao.secret_manager import SecretManager

class TestSecretManager(TestCase):
    def test_secret_manager_should_provide_secrets_as_properties(self):
        #given
        under_test = SecretManager(secret_storage="tests/dao/test_secrets.toml")
        content = {
            'tmdb': {
                'rate_limit': 200,
                'auth': {
                    'bearer_token': "bearer_token"
                },
                'URLs':{
                    'API_base_URL': "https://api.base.url/1",
                    'home_URL': "https://www.home.url/",
                    'image_URL': "https://image.url",
                }
            },
            'flask': {
                'secret_key': "secret_key"
            },
            'firebase': {
                'certificate': "certificate.json",
                'config': {
                    'apiKey': "apiKey",
                    'authDomain': "authDomain",
                    'projectId': "projectId",
                    'storageBucket': "storageBucket",
                    'messagingSenderId': "messagingSenderId",
                    'appId': "appId",
                    'databaseURL': ""
                }
            },
            'auth': {
                'store': "firebase"
            },
            'm2w': {
                'base_URL': "http://127.0.0.1:8080",
                'movie_retention': 3600
            },
            'neo4j': {
                'uri': "bolt://127.0.0.1:7687",
                'user': "neo4j",
                'password': "password"
            }
        }

        #when
        secrets = under_test.secrets

        #then
        self.assertEqual(secrets, content)
        self.assertEqual(under_test.tmdb_rate_limit, content['tmdb']['rate_limit'])
        self.assertEqual(under_test.tmdb_token, content['tmdb']['auth']['bearer_token'])
        self.assertEqual(under_test.tmdb_api, content['tmdb']['URLs']['API_base_URL'])
        self.assertEqual(under_test.tmdb_home, content['tmdb']['URLs']['home_URL'])
        self.assertEqual(under_test.tmdb_image, content['tmdb']['URLs']['image_URL'])
        self.assertEqual(under_test.flask_key, content['flask']['secret_key'])
        self.assertEqual(under_test.auth_store, content['auth']['store'])
        self.assertEqual(under_test.firebase_cert, content['firebase']['certificate'])
        self.assertEqual(under_test.firebase_config, content['firebase']['config'])
        self.assertEqual(under_test.m2w_base_url, content['m2w']['base_URL'])
        self.assertEqual(under_test.neo4j_uri, content['neo4j']['uri'])
        self.assertEqual(under_test.neo4j_user, content['neo4j']['user'])
        self.assertEqual(under_test.neo4j_pass, content['neo4j']['password'])
