from unittest import TestCase
from unittest.mock import MagicMock

from src.dao.secret_manager import SecretManager
from src.dao.m2w_database import M2WDatabase, M2wGroupHandler
from src.services.user_service import UserManagerService
from src.services.movie_caching import MovieCachingService
from src.services.group_service import GroupManagerService, GroupManagerServiceException, InvalidVoteError
from google.cloud import firestore

from collections.abc import Generator
from typing import Literal

class TestGroupManagerService(TestCase):
    def test_like_movie_should_pass_correct_paramaters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.user.add_movie_to_users_watchlist = MagicMock(return_value=True)
        under_test.user.get_blocklist = MagicMock(return_value="my_blocklist")
        under_test.movie.remove_movie_from_blocklist = MagicMock(return_value=True)

        #when
        response = under_test._like_movie(user_id="user_1", movie_id="1")

        #then
        self.assertEqual(response, True)
        under_test.user.add_movie_to_users_watchlist.assert_called_with(movie_id="1", user_id="user_1")
        under_test.user.get_blocklist.assert_called_with(user_id="user_1")
        under_test.movie.remove_movie_from_blocklist.assert_called_with(movie_id="1", blocklist="my_blocklist")

    def test_block_movie_should_pass_correct_paramaters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.user.remove_movie_from_users_watchlist = MagicMock(return_value=True)
        under_test.user.get_blocklist = MagicMock(return_value="my_blocklist")
        under_test.movie.add_movie_to_blocklist = MagicMock(return_value=True)

        #when
        response = under_test._block_movie(user_id="user_1", movie_id="1")

        #then
        self.assertEqual(response, True)
        under_test.user.remove_movie_from_users_watchlist.assert_called_with(movie_id="1", user_id="user_1")
        under_test.user.get_blocklist.assert_called_with(user_id="user_1")
        under_test.movie.add_movie_to_blocklist.assert_called_with(movie_id="1", blocklist="my_blocklist")

    def test_vote_for_movie_by_user_should_pass_like_correctly(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test._like_movie = MagicMock(return_value=True)
        under_test._block_movie = MagicMock(return_value=True)

        #when
        response = under_test.vote_for_movie_by_user(movie_id="1", user_id="user_1", vote='like')

        #then
        self.assertEqual(response, True)
        under_test._like_movie.assert_called_with(movie_id="1", user_id="user_1")
        under_test._block_movie.assert_not_called()

    def test_vote_for_movie_by_user_should_pass_blocked_correctly(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test._like_movie = MagicMock(return_value=True)
        under_test._block_movie = MagicMock(return_value=True)

        #when
        response = under_test.vote_for_movie_by_user(movie_id="1", user_id="user_1", vote='block')

        #then
        self.assertEqual(response, True)
        under_test._block_movie.assert_called_with(movie_id="1", user_id="user_1")
        under_test._like_movie.assert_not_called()

    def test_vote_for_movie_by_user_should_raise_InvalidVoteError(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test._like_movie = MagicMock(return_value=True)
        under_test._block_movie = MagicMock(return_value=True)

        #when
        with self.assertRaises(InvalidVoteError) as context:
            response = under_test.vote_for_movie_by_user(movie_id="1", user_id="user_1", vote='somevote')

        #then
        self.assertIsInstance(context.exception, InvalidVoteError)

    def test_get_watchgroup_data_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        data = MagicMock(firestore.DocumentSnapshot)
        data.to_dict = MagicMock(return_value={"group":"data"})
        under_test.group.get_one = MagicMock(return_value=data)

        #when
        response = under_test.get_watchgroup_data(group_id="group_1")

        #then
        self.assertEqual(response, {"group":"data"})
        under_test.group.get_one.assert_called_with(id_="group_1")

    def test_get_all_members_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.group.get_all_group_members = MagicMock(return_value=["members"])

        #when
        response = under_test.get_all_members(group_id="group_1")

        #then
        self.assertEqual(response, ["members"])
        under_test.group.get_all_group_members.assert_called_with(group_id="group_1")

    def test_get_combined_watchlist_of_members_should_pass_correct_parameters(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.movie.get_combined_watchlist_of_users = MagicMock(return_value=["movies"])

        #when
        response = under_test.get_combined_watchlist_of_members(users=["members"])

        #then
        self.assertEqual(response, ["movies"])
        under_test.movie.get_combined_watchlist_of_users.assert_called_with(users=["members"])

    def test_convert_genres_should_return_correct_list(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        genres = [
            {"name": "action"},
            {"name": "adventure"},
            {"name": "fantasy"}
        ]

        #when
        response = under_test.convert_genres(genres=genres)

        #then
        self.assertEqual(response, "action, adventure, fantasy")

    def test_get_raw_group_content_from_votes_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        votes = {
            1:{
                "user_1": "liked",
                "user_2": "blocked"
            },
            2:{
                "user_1": "blocked"
            },
            3:{
                "user_1": "blocked",
                "user_2": "liked"
            }
        }
        def details(movie_id):
            return {
                "title": f"The {movie_id}"
            }
        under_test.movie.get_movie_details = MagicMock(side_effect=details)

        #when
        response = under_test.get_raw_group_content_from_votes(votes=votes)

        #then
        self.assertEqual(response, {
            1:{
                "title": "The 1",
                "votes":{
                    "user_1": "liked",
                    "user_2": "blocked"
                }
            }
            ,
            3:{
                "title": "The 3",
                "votes":{
                    "user_1": "blocked",
                    "user_2": "liked"
                }
            }
        })
        under_test.movie.get_movie_details.assert_called_with(movie_id=3)

    def test_process_votes_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        votes = {
            "u1": "liked",
            "u2": "liked",
            "u3": "blocked",
            "u4": "blocked"
        }
        def get_data(user_id):
            return {
                'nickname':user_id,
                'email':f"{user_id}@mail.com",
                'profile_pic': f"{user_id}.png"
            }
        under_test.user.get_m2w_user_profile_data = MagicMock(side_effect=get_data)

        #when
        response = under_test.process_votes(votes=votes, primary_user="u1")

        #then
        self.assertEqual(response, {
            "primary_vote": "liked",
            "liked": [
                {
                    'nickname':"u2",
                    'email':"u2@mail.com",
                    'profile_pic': "u2.png"
                }
            ],
            "blocked": [
                {
                    'nickname':"u3",
                    'email':"u3@mail.com",
                    'profile_pic': "u3.png"
                },
                {
                    'nickname':"u4",
                    'email':"u4@mail.com",
                    'profile_pic': "u4.png"
                }
            ]
        })
        under_test.user.get_m2w_user_profile_data.assert_called_with(user_id='u4')

    def test_process_providers_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        secrets = MagicMock(SecretManager)
        secrets.tmdb_image = "TMBDi"
        under_test = GroupManagerService(
            secrets=secrets,
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "AA":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ]
            },
            "XX":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ],
                "buy":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 2,
                        "provider_name": "Notflex",
                        "display_priority": 2
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ],
                "rent":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 3,
                        "provider_name": "Gaggle play",
                        "display_priority": 3
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ],
            "buy_or_rent":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 2,
                    "provider_name": "Notflex",
                    "display_priority": 2
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 3,
                    "provider_name": "Gaggle play",
                    "display_priority": 3
                }
            ]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_process_providers_should_return_partial_if_flatrate_is_missing(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        secrets = MagicMock(SecretManager)
        secrets.tmdb_image = "TMBDi"
        under_test = GroupManagerService(
            secrets=secrets,
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "XX":{
                "link":"URL",
                "buy":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 2,
                        "provider_name": "Notflex",
                        "display_priority": 2
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ],
                "rent":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 3,
                        "provider_name": "Gaggle play",
                        "display_priority": 3
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[],
            "buy_or_rent":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 2,
                    "provider_name": "Notflex",
                    "display_priority": 2
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 3,
                    "provider_name": "Gaggle play",
                    "display_priority": 3
                }
            ]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_process_providers_should_return_partial_if_buy_is_missing(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        secrets = MagicMock(SecretManager)
        secrets.tmdb_image = "TMBDi"
        under_test = GroupManagerService(
            secrets=secrets,
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "XX":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ],
                "rent":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 3,
                        "provider_name": "Gaggle play",
                        "display_priority": 3
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ],
            "buy_or_rent":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 3,
                    "provider_name": "Gaggle play",
                    "display_priority": 3
                }
            ]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_process_providers_should_return_partial_if_rent_is_missing(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        secrets = MagicMock(SecretManager)
        secrets.tmdb_image = "TMBDi"
        under_test = GroupManagerService(
            secrets=secrets,
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "XX":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ],
                "buy":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 2,
                        "provider_name": "Notflex",
                        "display_priority": 2
                    },
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ],
            "buy_or_rent":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 2,
                    "provider_name": "Notflex",
                    "display_priority": 2
                },
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_process_providers_should_return_partial_if_buy_and_rent_missing(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        secrets = MagicMock(SecretManager)
        secrets.tmdb_image = "TMBDi"
        under_test = GroupManagerService(
            secrets=secrets,
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "XX":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[
                {
                    "logo_path": "TMBDi/t/p/original/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ],
            "buy_or_rent":[]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_process_providers_should_return_empty_if_locale_is_missing(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_watchgroup_data = MagicMock(return_value={"locale":"XX"})
        prov = {
            "AA":{
                "link":"URL",
                "flatrate":[
                    {
                        "logo_path": "/logo.jpg",
                        "provider_id": 1,
                        "provider_name": "Prime Provider",
                        "display_priority": 1
                    }
                ]
            }
        }

        #when
        response = under_test.process_providers(providers=prov, group_id="gr1")

        #then
        self.assertEqual(response, {
            "stream":[],
            "buy_or_rent":[]
        })
        under_test.get_watchgroup_data.assert_called_with(group_id="gr1")

    def test_get_group_votes_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        member0 = MagicMock(firestore.DocumentSnapshot)
        member0.id = "user_0"
        member1 = MagicMock(firestore.DocumentSnapshot)
        member1.id = "user_1"
        under_test.get_all_members = MagicMock(return_value=[member0, member1])
        
        def get_watchlist(user_id):
            watchlist = {
                "user_0":[
                    {
                        'id':0
                    },
                    {
                        'id':2
                    }
                ],
                "user_1":[
                    {
                        'id':1
                    },
                ]
            }
            return watchlist[user_id]
        under_test.user.get_movies_watchlist = MagicMock(side_effect=get_watchlist)
        
        def get_blocklist(user_id):
            blocklist = MagicMock(firestore.CollectionReference)
            mov0 = MagicMock(firestore.DocumentSnapshot)
            mov0.id = "0"
            mov1 = MagicMock(firestore.DocumentSnapshot)
            mov1.id = "1"
            mov2 = MagicMock(firestore.DocumentSnapshot)
            mov2.id = "2"
            if user_id == "user_0":
                blocklist.stream = MagicMock(return_value=[mov1])
            if user_id == "user_1":
                blocklist.stream = MagicMock(return_value=[mov2])
            return blocklist

        under_test.user.get_blocklist = MagicMock(side_effect=get_blocklist)
        under_test.movie.remove_movie_from_blocklist = MagicMock(return_value="success")

        #when
        result = under_test.get_group_votes(group_id="gr1")

        #then
        self.assertEqual(result, {
            0:{
                "user_0":"liked"
            },
            1:{
                "user_0":"blocked",
                "user_1":"liked"
            },
            2:{
                "user_0":"liked",
                "user_1":"blocked"
            }
        })
        under_test.get_all_members.assert_called_with(group_id="gr1")
        under_test.user.get_movies_watchlist.assert_called_with(user_id="user_1")
        under_test.user.get_blocklist.assert_called_with(user_id="user_1")
        under_test.movie.remove_movie_from_blocklist.assert_not_called()

    def test_get_group_votes_should_remove_from_blocklist_if_on_watchlist(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        member1 = MagicMock(firestore.DocumentSnapshot)
        member1.id = "user_1"
        under_test.get_all_members = MagicMock(return_value=[member1])
        
        def get_watchlist(user_id):
            watchlist = {
                "user_1":[
                    {
                        'id':1
                    },
                ]
            }
            return watchlist[user_id]
        under_test.user.get_movies_watchlist = MagicMock(side_effect=get_watchlist)
        
        blocklist = MagicMock(firestore.CollectionReference)
        mov0 = MagicMock(firestore.DocumentSnapshot)
        mov0.id = "0"
        mov1 = MagicMock(firestore.DocumentSnapshot)
        mov1.id = "1"
        mov2 = MagicMock(firestore.DocumentSnapshot)
        mov2.id = "2"
        blocklist.stream = MagicMock(return_value=[mov0, mov1, mov2])

        under_test.user.get_blocklist = MagicMock(return_value=blocklist)
        under_test.movie.remove_movie_from_blocklist = MagicMock(return_value="success")

        #when
        under_test.get_group_votes(group_id="gr1")

        #then
        under_test.get_all_members.assert_called_with(group_id="gr1")
        under_test.user.get_movies_watchlist.assert_called_with(user_id="user_1")
        under_test.user.get_blocklist.assert_called_with(user_id="user_1")
        under_test.movie.remove_movie_from_blocklist.assert_called_once()
        under_test.movie.remove_movie_from_blocklist.assert_called_with(
            movie_id="1",
            blocklist=blocklist
        )

    def test_get_group_content_should_sort_by_title(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_group_votes = MagicMock(return_value="success")
        raw ={
            2:{
                'id': 2,
                'title': 'Brave the Titular',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 2,
                'votes': 2
            },
            3:{
                'id': 3,
                'title': 'Choclate Titles',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 3,
                'votes': 3
            },
            1:{
                'id': 1,
                'title': 'Almost the Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 1,
                'votes': 1
            }
        }
        under_test.get_raw_group_content_from_votes = MagicMock(return_value=raw)
        class secret_class():
            def __init__(self) -> None:
                self.tmdb_image = "TMDBimg"
                self.tmdb_home = "TMDB"
        under_test._secrets = secret_class()
        under_test.convert_genres = MagicMock(return_value='Action, Adventure')
        
        def providers(providers, group_id):
            prov = {
                1:{
                    "stream":[],
                    "buy_or_rent":[]
                },
                2:{
                    "stream":[],
                    "buy_or_rent":[]
                },
                3:{
                    "stream":[],
                    "buy_or_rent":[]
                }
            }
            return prov[providers]
        under_test.process_providers = MagicMock(side_effect=providers)

        def votes(votes, primary_user):
            my_votes = {
                1:{
                    "primary_vote": "liked",
                    "liked": [],
                    "blocked": []
                },
                2:{
                    "primary_vote": "liked",
                    "liked": [],
                    "blocked": []
                },
                3:{
                    "primary_vote": "liked",
                    "liked": [],
                    "blocked": []
                }
            }
            return my_votes[votes]
        under_test.process_votes = MagicMock(side_effect=votes)

        #when
        result = under_test.get_group_content(group_id="gr1", primary_user="user1")
        sorted_result = [elem['id'] for elem in result]

        #then
        self.assertEqual(sorted_result, [1, 2, 3])

    def test_get_group_content_should_sort_by_votes(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_group_votes = MagicMock(return_value="success")
        raw ={
            2:{
                'id': 2,
                'title': 'The Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 2,
                'votes': 2
            },
            3:{
                'id': 3,
                'title': 'The Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 3,
                'votes': 3
            },
            1:{
                'id': 1,
                'title': 'The Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 1,
                'votes': 1
            }
        }
        under_test.get_raw_group_content_from_votes = MagicMock(return_value=raw)
        class secret_class():
            def __init__(self) -> None:
                self.tmdb_image = "TMDBimg"
                self.tmdb_home = "TMDB"
        under_test._secrets = secret_class()
        under_test.convert_genres = MagicMock(return_value='Action, Adventure')
        
        def providers(providers, group_id):
            prov = {
                1:{
                    "stream":[],
                    "buy_or_rent":[]
                },
                2:{
                    "stream":[],
                    "buy_or_rent":[]
                },
                3:{
                    "stream":[],
                    "buy_or_rent":[]
                }
            }
            return prov[providers]
        under_test.process_providers = MagicMock(side_effect=providers)

        def votes(votes, primary_user):
            my_votes = {
                1:{
                    "primary_vote": "liked",
                    "liked": [1, 2],
                    "blocked": [1]
                },
                2:{
                    "primary_vote": "liked",
                    "liked": [1],
                    "blocked": [1, 2]
                },
                3:{
                    "primary_vote": "liked",
                    "liked": [],
                    "blocked": [1]
                }
            }
            return my_votes[votes]
        under_test.process_votes = MagicMock(side_effect=votes)

        #when
        result = under_test.get_group_content(group_id="gr1", primary_user="user1")
        sorted_result = [elem['id'] for elem in result]

        #then
        self.assertEqual(sorted_result, [1, 2, 3])

    def test_get_group_content_should_sort_by_providers(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_group_votes = MagicMock(return_value="success")
        raw ={
            2:{
                'id': 2,
                'title': 'Brave the Titular',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 2,
                'votes': 2
            },
            3:{
                'id': 3,
                'title': 'Choclate Titles',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 3,
                'votes': 3
            },
            1:{
                'id': 1,
                'title': 'Almost the Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 1,
                'votes': 1
            }
        }
        under_test.get_raw_group_content_from_votes = MagicMock(return_value=raw)
        class secret_class():
            def __init__(self) -> None:
                self.tmdb_image = "TMDBimg"
                self.tmdb_home = "TMDB"
        under_test._secrets = secret_class()
        under_test.convert_genres = MagicMock(return_value='Action, Adventure')
        
        def providers(providers, group_id):
            prov = {
                1:{
                    "stream":[],
                    "buy_or_rent":[]
                },
                2:{
                    "stream":[],
                    "buy_or_rent":[1,2,3,4,5]
                },
                3:{
                    "stream":[1],
                    "buy_or_rent":[]
                }
            }
            return prov[providers]
        under_test.process_providers = MagicMock(side_effect=providers)

        def votes(votes, primary_user):
            my_votes = {
                1:{
                    "primary_vote": "liked",
                    "liked": [1, 2],
                    "blocked": [1]
                },
                2:{
                    "primary_vote": "liked",
                    "liked": [1, 2],
                    "blocked": [1]
                },
                3:{
                    "primary_vote": "liked",
                    "liked": [1, 2],
                    "blocked": [1]
                }
            }
            return my_votes[votes]
        under_test.process_votes = MagicMock(side_effect=votes)

        #when
        result = under_test.get_group_content(group_id="gr1", primary_user="user1")
        sorted_result = [elem['id'] for elem in result]

        #then
        self.assertEqual(sorted_result, [3,2,1])

    def test_get_group_content_should_sort_by_primary_votes(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_group_votes = MagicMock(return_value="success")
        raw ={
            2:{
                'id': 2,
                'title': 'Brave the Titular',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 2,
                'votes': 2
            },
            3:{
                'id': 3,
                'title': 'Choclate Titles',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 3,
                'votes': 3
            },
            1:{
                'id': 1,
                'title': 'Almost the Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': 1,
                'votes': 1
            }
        }
        under_test.get_raw_group_content_from_votes = MagicMock(return_value=raw)
        class secret_class():
            def __init__(self) -> None:
                self.tmdb_image = "TMDBimg"
                self.tmdb_home = "TMDB"
        under_test._secrets = secret_class()
        under_test.convert_genres = MagicMock(return_value='Action, Adventure')
        
        def providers(providers, group_id):
            prov = {
                1:{
                    "stream":[],
                    "buy_or_rent":[1,2,3,4,5]
                },
                2:{
                    "stream":[1],
                    "buy_or_rent":[]
                },
                3:{
                    "stream":[1],
                    "buy_or_rent":[1]
                }
            }
            return prov[providers]
        under_test.process_providers = MagicMock(side_effect=providers)

        def votes(votes, primary_user):
            my_votes = {
                1:{
                    "primary_vote": "Blocked",
                    "liked": [1, 2],
                    "blocked": [1]
                },
                2:{
                    "primary_vote": "liked",
                    "liked": [1],
                    "blocked": [1]
                },
                3:{
                    "primary_vote": None,
                    "liked": [],
                    "blocked": [1]
                }
            }
            return my_votes[votes]
        under_test.process_votes = MagicMock(side_effect=votes)

        #when
        result = under_test.get_group_content(group_id="gr1", primary_user="user1")
        sorted_result = [elem['id'] for elem in result]

        #then
        self.assertEqual(sorted_result, [3,2,1])

    def test_get_group_content_should_return_dict(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.get_group_votes = MagicMock(return_value="success")
        raw ={
            1:{
                'id': 1,
                'title': 'The Title',
                'poster_path': "/poster.png",
                'release_date': '2024-01-01',
                'genres': 'genres',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'local_providers': "prov",
                'votes': 'votes'
            }
        }
        under_test.get_raw_group_content_from_votes = MagicMock(return_value=raw)
        class secret_class():
            def __init__(self) -> None:
                self.tmdb_image = "TMDBimg"
                self.tmdb_home = "TMDB"
        under_test._secrets = secret_class()
        under_test.convert_genres = MagicMock(return_value='Action, Adventure')
        under_test.process_providers = MagicMock(return_value={
            "stream":[
                {
                    "logo_path": "/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                }
            ],
            "buy_or_rent":[
                {
                    "logo_path": "/logo.jpg",
                    "provider_id": 2,
                    "provider_name": "Notflex",
                    "display_priority": 2
                },
                {
                    "logo_path": "/logo.jpg",
                    "provider_id": 1,
                    "provider_name": "Prime Provider",
                    "display_priority": 1
                },
                {
                    "logo_path": "/logo.jpg",
                    "provider_id": 3,
                    "provider_name": "Gaggle play",
                    "display_priority": 3
                }
            ]
        })
        under_test.process_votes = MagicMock(return_value={
            "primary_vote": "liked",
            "liked": [
                {
                    'nickname':"u2",
                    'email':"u2@mail.com",
                    'profile_pic': "u2.png"
                }
            ],
            "blocked": [
                {
                    'nickname':"u3",
                    'email':"u3@mail.com",
                    'profile_pic': "u3.png"
                },
                {
                    'nickname':"u4",
                    'email':"u4@mail.com",
                    'profile_pic': "u4.png"
                }
            ]
        })

        #when
        result = under_test.get_group_content(group_id="gr1", primary_user="user1")

        #then
        self.assertEqual(result, [
            {
                'id': 1,
                'title': 'The Title',
                'poster_path': "TMDBimg/t/p/original/poster.png",
                'release_date': '2024-01-01',
                'genres': 'Action, Adventure',
                'runtime': 123,
                'overview': 'The time of View is over!',
                'official_trailer': 'ytURL/v=trailer',
                'tmdb': f"TMDB/movie/1",
                'providers': {
                    "stream":[
                        {
                            "logo_path": "/logo.jpg",
                            "provider_id": 1,
                            "provider_name": "Prime Provider",
                            "display_priority": 1
                        }
                    ],
                    "buy_or_rent":[
                        {
                            "logo_path": "/logo.jpg",
                            "provider_id": 2,
                            "provider_name": "Notflex",
                            "display_priority": 2
                        },
                        {
                            "logo_path": "/logo.jpg",
                            "provider_id": 1,
                            "provider_name": "Prime Provider",
                            "display_priority": 1
                        },
                        {
                            "logo_path": "/logo.jpg",
                            "provider_id": 3,
                            "provider_name": "Gaggle play",
                            "display_priority": 3
                        }
                    ]
                },
                'votes': {
                    "primary_vote": "liked",
                    "liked": [
                        {
                            'nickname':"u2",
                            'email':"u2@mail.com",
                            'profile_pic': "u2.png"
                        }
                    ],
                    "blocked": [
                        {
                            'nickname':"u3",
                            'email':"u3@mail.com",
                            'profile_pic': "u3.png"
                        },
                        {
                            'nickname':"u4",
                            'email':"u4@mail.com",
                            'profile_pic': "u4.png"
                        }
                    ]
                }
            }
        ])
        under_test.get_group_votes.assert_called_with(group_id="gr1")
        under_test.get_raw_group_content_from_votes(votes="success")
        under_test.convert_genres.assert_called_with('genres')
        under_test.process_providers.assert_called_with(providers="prov", group_id="gr1")
        under_test.process_votes.assert_called_with(votes='votes', primary_user="user1")
    
    def test_watch_movie_by_user_should_return_true(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.vote_for_movie_by_user = MagicMock(return_value=True)

        #when
        response = under_test.watch_movie_by_user(movie_id=1, user_id="user_1")

        #then
        self.assertEqual(response, True)
        under_test.vote_for_movie_by_user.assert_called_with(movie_id="1", user_id="user_1", vote='block')

    def test_watch_movie_by_group_should_return_true(self):
        #given
        m2w_db = MagicMock(M2WDatabase)
        m2w_db.group = MagicMock(M2wGroupHandler)
        under_test = GroupManagerService(
            secrets=MagicMock(SecretManager),
            m2w_db=m2w_db,
            user_service=MagicMock(UserManagerService),
            movie_service=MagicMock(MovieCachingService)
        )
        under_test.watch_movie_by_user = MagicMock(return_value=True)
        member = MagicMock(firestore.DocumentSnapshot)
        member.id = "mem_1"
        under_test.get_all_members = MagicMock(return_value=[member])

        #when
        response = under_test.watch_movie_by_group(movie_id=1, group_id="gr_1")

        #then
        self.assertEqual(response, True)
        under_test.watch_movie_by_user.assert_called_with(movie_id=1, user_id="mem_1")


        
    # def watch_movie_by_group(self, movie_id: Union[int, str], group_id: str):
    #     """Watch a movie with a group together.
        
    #     Parameters
    #     ----------
    #     movie_id: the ID of the movie.
    #     group_id: the M2W ID of the group. 

    #     Returns
    #     -------
    #     True if successful, False otherwise.
    #     """
    #     try:
    #         users = self.get_all_members(group_id=group_id)
    #         for user in users:
    #             self.watch_movie_by_user(movie_id=movie_id, user_id=user.id)
    #     except Exception as e:
    #         raise GroupManagerServiceException(e)
    #     else:
    #         return True