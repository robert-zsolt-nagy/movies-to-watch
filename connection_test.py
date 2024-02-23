import tomllib
import requests
import webbrowser
from typing import Optional
from src.tmdb.authenticate import Authentication, Account
from src.tmdb.movies import Movie
from src.m2w.groups import watch_group



# image path: https://image.tmdb.org/t/p/original{"poster_path"}

# trailer path: https://www.youtube.com/watch?v={"key"}
    # {
    #   "iso_639_1": "en",
    #   "iso_3166_1": "US",
    #   "name": "#TBT Trailer",
    #   "key": "BdJKm16Co6M",
    #   "site": "YouTube",
    #   "size": 1080,
    #   "type": "Trailer",
    #   "official": true,
    #   "published_at": "2014-10-02T19:20:22.000Z",
    #   "id": "5c9294240e0a267cd516835f"
    # }

if __name__ == "__main__":
    authenticator = Authentication()

    # payload = authenticator.create_request_token()
    # print(authenticator.ask_user_permission())
    # permit = input("Permitted?")
    # if permit == "y":
    #     new_session = authenticator.create_session_id(payload=payload)
    #     print(f"session_id:{new_session}")
    
    SESSION_ID = authenticator.secrets['tmdb']['session_id']
    TOKEN = authenticator.secrets['tmdb']['bearer_token']
    SESSIONS = authenticator.secrets['tmdb']['session_ids']

    members = []
    for sesh in SESSIONS:
        account_data = authenticator.get_account_data(session_id=sesh)
        my_account = Account(token=TOKEN, session_id=sesh, **account_data)
        members.append(my_account)
    my_group = watch_group(memebers=members)
    movie_union = []
    for elem in my_group.get_grouplist_union():
        print(elem)
        mov = Movie(id=elem['id'], token=TOKEN)
        movie_union.append(mov)
    print(movie_union)



    #     my_lists = my_account.get_lists()
    # print("My lists:")
    # for elem in my_lists:
    #     print(elem['name'])
    # watchlist = my_account.get_watchlist_movie()
    # print("Watchlist movies:")
    # for movie in watchlist:
    #     mov = Movie(id=movie['id'], token=TOKEN)
    #     # print(mov.id, mov.title, mov.watch_providers, mov.status)
    #     try:
    #         print(mov.id, mov.title, mov.watch_providers['HU'])
    #     except KeyError:
    #         print(mov.id, mov.title, 'not available')