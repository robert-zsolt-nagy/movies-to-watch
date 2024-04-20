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
            'firestore': {
                'project': "project",
                'certificate': "certificate.json"
            },
            'm2w': {
                'base_URL': "http://127.0.0.1:8080",
                'movie_retention': 3600
            }
        }

        #when
        secrets = under_test.secrets

        #then
        self.assertEqual(secrets, content)
        self.assertEqual(under_test.tmdb_rate_limit, content['tmdb']['rate_limit'])
        self.assertEqual(under_test.tmdb_token, content['tmdb']['auth']['bearer_token'])
        self.assertEqual(under_test.tmdb_API, content['tmdb']['URLs']['API_base_URL'])
        self.assertEqual(under_test.tmdb_home, content['tmdb']['URLs']['home_URL'])
        self.assertEqual(under_test.tmdb_image, content['tmdb']['URLs']['image_URL'])
        self.assertEqual(under_test.flask_key, content['flask']['secret_key'])
        self.assertEqual(under_test.firebase_cert, content['firebase']['certificate'])
        self.assertEqual(under_test.firebase_config, content['firebase']['config'])
        self.assertEqual(under_test.firestore_cert, content['firestore']['certificate'])
        self.assertEqual(under_test.firestore_project, content['firestore']['project'])
        self.assertEqual(under_test.m2w_base_URL, content['m2w']['base_URL'])
        self.assertEqual(under_test.m2w_movie_retention, content['m2w']['movie_retention'])