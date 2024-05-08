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
            2:{
                "title": "The 2",
                "votes":{
                    "user_1": "blocked"
                }
            }
        })
        under_test.movie.get_movie_details.assert_called_with(movie_id=2)

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



  




####### original data from the class
    # def process_providers(self, providers: dict, group_id: str) -> dict:
    #     datasheet = {
    #         "stream":[],
    #         "buy_or_rent":[]
    #     }
    #     try:
    #         group_data = self.get_watchgroup_data(group_id=group_id)
    #         locale = group_data.get("locale", "HU")
    #         local_providers = providers.get(locale, False)
    #         if local_providers:
    #             # collect stream
    #             stream = local_providers.get("flatrate", False)
    #             if stream:
    #                 datasheet['stream'] = stream
    #             # compile buy and rent
    #             buy_or_rent = {}
    #             buy = local_providers.get('buy', False)
    #             if buy:
    #                 for current in buy:
    #                     buy_or_rent[current["provider_id"]] = current
    #             rent = local_providers.get('rent', False)
    #             if rent:
    #                 for current in rent:
    #                     buy_or_rent[current["provider_id"]] = current
    #             if buy_or_rent:
    #                 datasheet['buy_or_rent'] = [prov for prov in buy_or_rent.values()]
    #     except Exception:
    #         return {
    #             "stream":[],
    #             "buy_or_rent":[]
    #         }
    #     else:
    #         return datasheet

    # def get_group_votes(self, group_id: str) -> dict:
    #     try:
    #         # get all members
    #         all_members = self.get_all_members(group_id=group_id)
    #         # collect lists
    #         vote_map = {}
    #         for member in all_members:
    #             # get watchlist
    #             watchlist = self.user.get_movies_watchlist(user_id=member.id)
    #             # get blocklist
    #             blocklist_ref = self.user.get_blocklist(user_id=member.id)
    #             # register votes
    #             for movie in watchlist:
    #                 # register "liked" if on watchlist
    #                 if vote_map.get(movie['id'], False):
    #                     vote_map[movie['id']][member.id] = "liked"
    #                 else:
    #                     vote_map[movie['id']] = {}
    #                     vote_map[movie['id']][member.id] = "liked"
    #                 # remove from user's blocklist if on user's watchlist
    #                 for blocked_movie in blocklist_ref.stream():
    #                     if int(blocked_movie.id) == movie['id']:
    #                         self.movie.remove_movie_from_blocklist(
    #                             movie_id=str(movie['id']),
    #                             blocklist=blocklist_ref
    #                             )
    #                         break
    #             for blocked_movie in blocklist_ref.stream():
    #                 # register "blocked" if on blocklist
    #                 _id = int(blocked_movie.id)
    #                 if vote_map.get(_id, False):
    #                     vote_map[_id][member.id] = "blocked"
    #                 else:
    #                     vote_map[_id] = {}
    #                     vote_map[_id][member.id] = "blocked"
    #     except Exception:
    #         raise GroupManagerServiceException('Error during vote collection.')
    #     else:
    #         return vote_map
        
    
        
    # def get_group_content(self, group_id: str, primary_user: str) -> list[dict]:
    #     try:
    #         watchlist = []
    #         votes = self.get_group_votes(group_id=group_id)
    #         raw_content = self.get_raw_group_content_from_votes(votes=votes)
    #         for movie_id, details in raw_content.items():
    #             datasheet = {
    #                 'id': details['id'],
    #                 'title': details['title'],
    #                 'poster_path': None,
    #                 'release_date': details['release_date'],
    #                 'genres': None,
    #                 'runtime': details['runtime'],
    #                 'overview': details['overview'],
    #                 'official_trailer': details['official_trailer'],
    #                 'tmdb': None,
    #                 'providers': None,
    #                 'votes': None
    #             }
    #             # convert poster path
    #             poster_path = f"{self.__secrets.tmdb_image}/t/p/original{details['poster_path']}"
    #             datasheet['poster_path'] = poster_path
    #             # convert genres
    #             datasheet['genres'] = self.convert_genres(details['genres'])
    #             # fill tmdb
    #             tmdb = f"{self.__secrets.tmdb_home}/movie/{details['id']}"
    #             datasheet['tmdb'] = tmdb
    #             # process providers
    #             datasheet['providers'] = self.process_providers(providers=details['local_providers'], group_id=group_id)
    #             # process votes
    #             datasheet['votes'] = self.process_votes(votes=details['votes'], primary_user=primary_user)
    #             watchlist.append(datasheet)
    #         # sort watchlist
    #         def by_title(value):
    #             return value['title']
    #         watchlist.sort(key=by_title)
    #         def by_vote(value):
    #             votes = value['votes']
    #             result = len(votes['liked']) + len(votes['blocked'])
    #             return result
    #         watchlist.sort(key=by_vote, reverse=True)
    #         def by_provider(value):
    #             stream = value['providers']['stream']
    #             buy_or_rent = value['providers']['buy_or_rent']
    #             score = len(stream)*10 + len(buy_or_rent)
    #             return score
    #         watchlist.sort(key=by_provider, reverse=True)
    #     except Exception:
    #         raise GroupManagerServiceException("Error during group content creation.")
    #     else:
    #         return watchlist

    
        
    
        
    
        
