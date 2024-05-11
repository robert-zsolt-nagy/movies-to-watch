import json
from typing import Optional
import os

import pyrebase
from flask import Flask, render_template, session, redirect, request, flash
from flask_apscheduler import APScheduler
from google.oauth2 import service_account
from requests.exceptions import HTTPError
import requests

from src.dao.secret_manager import SecretManager
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.m2w_database import M2WDatabase
from src.dao.authentication_manager import AuthenticationManager
from src.dao.tmdb_user_repository import TmdbUserRepository

from src.services.movie_caching import MovieCachingService
from src.services.user_service import UserManagerService, WeakPasswordError, EmailMismatchError, PasswordMismatchError
from src.services.group_service import GroupManagerService

# reading the secrets
if os.getenv("MoviesToWatch") == "test":
    SECRETS = SecretManager('secrets_test.toml')
else:
    SECRETS = SecretManager('secrets.toml')

# connect to database
m2w_db_cert = service_account.Credentials.from_service_account_file(SECRETS.firestore_cert)

def get_firebase_error(error: HTTPError) -> str:
    """Get the error message from a raised error. """
    message = json.loads(error.args[1])
    return message['error']["message"]

def get_tmdb_http_client(session_: Optional[requests.Session]=None) -> TmdbHttpClient:
    return TmdbHttpClient(
        token=SECRETS.tmdb_token,
        base_url=SECRETS.tmdb_API,
        session=session_
    )

def get_m2w_db() -> M2WDatabase:
    return M2WDatabase(
        project=SECRETS.firestore_project,
        credentials=m2w_db_cert
    )

def get_auth() -> AuthenticationManager:
    return AuthenticationManager(
        config=SECRETS.firebase_config
    )

# setting up Flask
app = Flask(__name__)
app.secret_key = SECRETS.flask_key

# setting up firebase authentication
firebase_app = pyrebase.initialize_app(config=SECRETS.firebase_config)
firebase_auth = firebase_app.auth()

# setting up scheduler and jobs
scheduler = APScheduler()

@scheduler.task('cron', id="update_movies", hour='*', minute='*/15')
def update_movie_cache():
    """Updates the movies cache regularly."""
    try:
        MovieCachingService(
            tmdb_http_client=get_tmdb_http_client(),
            m2w_database=get_m2w_db(),
            m2w_movie_retention=SECRETS.m2w_movie_retention
            ).movie_cache_update_job()
    except Exception:
        pass
    else:
        pass


#setting up requests and endpoints
@app.route("/error")
def error():
    return render_template('error.html')

@app.route("/", methods=['POST', 'GET'])
def root():
    if 'user' in session:
        try:
            logged_on = session['user']
            user_manager = UserManagerService(
                m2w_db=get_m2w_db(),
                auth=get_auth(),
                user_repo=TmdbUserRepository(
                    tmdb_http_client=get_tmdb_http_client()
                )
            )
            user_data = user_manager.get_m2w_user_profile_data(user_id=logged_on)
            group = user_data["primary_group"]
        except Exception as e:
            return render_template("error.html", error=e)
        else:
            return render_template(
                "index.html", 
                logged_on=session['nickname'], 
                verified=session['emailVerified'],
                tmdb_linked=user_data['tmdb_session'],
                group=group
                )
    else:
        return redirect("/login")
    
        
@app.route("/logout")
def logout():
    try:
        keys = list(session.keys())
        for key in keys:
            session.pop(key)
    except KeyError:
        return redirect("/")
    else:
        return redirect("/")


@app.route("/login", methods=['POST', 'GET'])
def login():
    target = request.args.get("redirect", default="/")
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            user_service = UserManagerService(
                m2w_db=get_m2w_db(),
                auth=get_auth(),
                user_repo=TmdbUserRepository(
                    tmdb_http_client=get_tmdb_http_client()
                )
            )
            user = user_service.sign_in_and_update_tmdb_cache(email=email, password=password)
            for k, v in user.items():
                session[k] = v
        except Exception as e:
            return render_template("login.html", error=e, target=target)
        else:
            return redirect(target)
    else:
        if 'user' in session:
            return redirect(target)
        else:
            return render_template("login.html", target=target)


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            confirm_email = request.form.get('email_confirm')
            password = request.form.get('password')
            confirm_password = request.form.get('password_confirm')
            nickname = request.form.get('nickname')
            picture = "01.png"
            locale = "HU"
            if nickname == '':
                nickname = email.split('@')[0]
            user_service = UserManagerService(
                m2w_db=get_m2w_db(),
                auth=get_auth(),
                user_repo=TmdbUserRepository(
                    tmdb_http_client=get_tmdb_http_client()
                )
            )
            response = user_service.sign_up_user(
                email=email,
                confirm_email=confirm_email,
                password=password,
                confirm_password=confirm_password,
                nickname=nickname,
                picture=picture,
                locale=locale
            )
        except EmailMismatchError:
            return render_template(
                "signup.html", 
                error="Emails don't match!",
                email=email,
                email_c=confirm_email,
                password=password,
                password_c=confirm_password,
                nickname=nickname
                )
        except PasswordMismatchError:
            return render_template(
                "signup.html", 
                error="Passwords don't match!",
                email=email,
                email_c=confirm_email,
                nickname=nickname
                )
        except WeakPasswordError:
            return render_template(
                "signup.html", 
                error="Password must contain at least 6 characters!",
                email=email,
                email_c=confirm_email,
                nickname=nickname
                )
        except HTTPError as he:
            msg = get_firebase_error(he)
            return render_template(
                "signup.html", 
                error=msg,
                email=email,
                email_c=confirm_email,
                password=password,
                password_c=confirm_password,
                nickname=nickname
                )
        except Exception as e:
            return render_template(
                "signup.html", 
                error=e,
                email=email,
                email_c=confirm_email,
                password=password,
                password_c=confirm_password,
                nickname=nickname
                )
        else:
            return render_template("signup.html", success=response)
    else:
        return render_template("signup.html")


@app.route("/approved")
def approved():
    approval = request.args.get("approved")
    request_token = request.args.get("request_token")
    try:
        if (request_token == session['request_payload']) and (approval == "true"):
            try:
                user_service = UserManagerService(
                    m2w_db=get_m2w_db(),
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=get_tmdb_http_client()
                    )
                )
                tmdb_session = user_service.create_tmdb_session_for_user(request_token=request_token)
                user_service.update_user_data(user_id=session['user'], user_data={"tmdb_session": tmdb_session})
                user_service.update_tmdb_user_cache(user_id=session['user'])
            except Exception as err:
                return render_template("approved.html", success=False, error=err)
            else:
                return render_template("approved.html", success=True)
        else:
            return render_template("approved.html", success=False, error="Session not approved or invalid.")
    except Exception as err:
        return render_template("error.html", error=err)


@app.route("/profile")
def profile():
    if "user" in session:
        try:
            user_service = UserManagerService(
                m2w_db=get_m2w_db(),
                auth=get_auth(),
                user_repo=TmdbUserRepository(
                    tmdb_http_client=get_tmdb_http_client()
                )
            )
            user_data = user_service.get_m2w_user_profile_data(user_id=session['user'])
        except Exception as e:
            return render_template('error.html', error=e)
        else:
            return render_template('profile.html', profile_data=user_data, logged_on=session['user'])
    else:
        return redirect("/login?redirect=/profile")
    
@app.route("/link-to-tmdb")
def link_to_tmdb():
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            user_service = UserManagerService(
                m2w_db=get_m2w_db(),
                auth=get_auth(),
                user_repo=TmdbUserRepository(
                    tmdb_http_client=get_tmdb_http_client()
                )
            )
            response = user_service.init_link_user_profile_to_tmdb(
                redirect_to=f'{SECRETS.m2w_base_URL}/approved',
                tmdb_url=SECRETS.tmdb_home
            )
            session['request_payload'] = json.dumps(response["tmdb_request_token"])
            permission_URL = response["permission_URL"]
        except Exception as e:
            return render_template('error.html',  error=e)
        else:
            return redirect(permission_URL)
    else:
        return redirect("/login?redirect=/link-to-tmdb")
    

@app.route("/resend-verification")
def resend_verification():
    if 'user' in session:
        if session['emailVerified'] == False:
            try:
                user_service = UserManagerService(
                    m2w_db=get_m2w_db(),
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=get_tmdb_http_client()
                    )
                )
                account_data = user_service.get_firebase_user_account_info(user_idtoken=session['idToken'])
                if account_data['emailVerified']:
                    session['emailVerified'] = account_data['emailVerified']
                else:
                    firebase_auth.send_email_verification(id_token=session['idToken'])
            except Exception as e:
                flash(f"The following error occured: {e}")
                redirect('/error')
            else:
                if account_data['emailVerified']:
                    flash("Your email verification is already complete!")
                else:
                    flash("Please check your mailbox you should receive a verification email shortly!")
            return redirect('/error')
        else:
            flash("Your email verification is already complete!")
            return redirect('/error')
    else:
        return redirect("/login?redirect=/resend-verification")
    
@app.route("/api/group/<group>")
def group_content(group):
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            logged_on = session['user']
            m2w_db = get_m2w_db()
            tmdb_client = get_tmdb_http_client()
            group_service = GroupManagerService(
                secrets=SECRETS,
                m2w_db=m2w_db,
                user_service=UserManagerService(
                    m2w_db=m2w_db,
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=tmdb_client
                    )
                ),
                movie_service=MovieCachingService(
                    tmdb_http_client=tmdb_client,
                    m2w_database=m2w_db,
                    m2w_movie_retention=SECRETS.m2w_movie_retention
                )
            )
            movie_datasheets = group_service.get_group_content(
                group_id=group,
                primary_user=logged_on
            )
        except Exception as e:
            flash("The following error occured:")
            flash(e)
            return render_template("group_content.html", error=True)
        else:
            return render_template("group_content.html", movies=movie_datasheets, group=group)
    else:
        flash("You are not logged in!")
        return render_template("group_content.html", error=True)
    
@app.route("/api/vote/<movie>/<vote>")
def vote_for_movie(movie, vote):
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            logged_on = session['user']
            m2w_db = get_m2w_db()
            tmdb_client = get_tmdb_http_client()
            group_service = GroupManagerService(
                secrets=SECRETS,
                m2w_db=m2w_db,
                user_service=UserManagerService(
                    m2w_db=m2w_db,
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=tmdb_client
                    )
                ),
                movie_service=MovieCachingService(
                    tmdb_http_client=tmdb_client,
                    m2w_database=m2w_db,
                    m2w_movie_retention=SECRETS.m2w_movie_retention
                )
            )
            response = group_service.vote_for_movie_by_user(
                movie_id=movie,
                user_id=logged_on,
                vote=vote
            )
        except Exception as e:
            flash(f"The following error occurred: {e}")
            return render_template("vote_response.html", vote=vote, movie_id=movie, error=True)
        else:
            if response:
                return render_template("vote_response.html", vote=vote, movie_id=movie)
            else:
                flash("Unable to register vote.")
                return render_template("vote_response.html", vote=vote, movie_id=movie, error=True)
    else:
        target = f"/login?redirect=/api/vote/{movie}/{vote}"
        return redirect(target)
    
@app.route("/api/watched/<movie>/<group_id>", methods=['POST', 'GET'])
def watched_movie(movie, group_id):
    if ('user' in session) and (session['emailVerified'] == True):
        if request.method == 'GET':
            try:
                movie_service = MovieCachingService(
                    tmdb_http_client=get_tmdb_http_client(),
                    m2w_database=get_m2w_db(),
                    m2w_movie_retention=SECRETS.m2w_movie_retention
                )
                movie_data = movie_service.get_movie_details(movie_id=movie)
            except Exception as e:
                return redirect("/error", error=e)
            else:
                return render_template('watched_movie.html', movie=movie, 
                                       group_id=group_id, movie_title=movie_data['title'])
        if request.method == 'POST': 
            watchmode = request.form.get('watch_mode')
            try:
                logged_on = session['user']
                m2w_db = get_m2w_db()
                tmdb_client = get_tmdb_http_client()
                group_service = GroupManagerService(
                    secrets=SECRETS,
                    m2w_db=m2w_db,
                    user_service=UserManagerService(
                        m2w_db=m2w_db,
                        auth=get_auth(),
                        user_repo=TmdbUserRepository(
                            tmdb_http_client=tmdb_client
                        )
                    ),
                    movie_service=MovieCachingService(
                        tmdb_http_client=tmdb_client,
                        m2w_database=m2w_db,
                        m2w_movie_retention=SECRETS.m2w_movie_retention
                    )
                )
                movie_data = group_service.movie.get_movie_details(movie_id=movie)
                if watchmode == 'alone':
                    group_service.watch_movie_by_user(movie_id=movie, user_id=logged_on)
                else:
                    group_service.watch_movie_by_group(movie_id=movie, group_id=group_id)
            except Exception as e:
                return redirect("/error", error=e)
            else:
                if watchmode == 'alone':
                    flash(f"You watched: {movie_data['title']}")
                    return redirect("/")
                else:
                    flash(f"Your Group watched: {movie_data['title']}")
                    return redirect("/")
    

# starting scheduler
if os.getenv("MoviesToWatch") != "test":
    scheduler.init_app(app)
    scheduler.start()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

