import json
from datetime import datetime, timedelta

import pyrebase
from flask import Flask, render_template, session, redirect, request, flash, url_for
from flask_apscheduler import APScheduler
from google.cloud import firestore
from google.oauth2 import service_account
from requests.exceptions import HTTPError

from src.authenticate import SecretManager, Authentication, Account
from src.groups import fsWatchGroup, add_to_blocklist, remove_from_blocklist
from src.movies import Movie

# reading the secrets
secrets = SecretManager()

# conenct to database
db_cert = service_account.Credentials.from_service_account_file(secrets.firestore_cert)
db = firestore.Client(project=secrets.firestore_project, credentials=db_cert)

# setting upo tmdb
tmdb_auth = Authentication(secrets=secrets.secrets)

def get_firebase_error(error: HTTPError) -> str:
    """Get the error message from a raised error. """
    message = json.loads(error.args[1])
    return message['error']["message"]

# setting up Flask
app = Flask(__name__)
app.secret_key = secrets.secrets['flask']['secret_key']

# setting up firebase authentication
firebase_app = pyrebase.initialize_app(config=secrets.firebase_config)
firebase_auth = firebase_app.auth()

# setting up scheduler and jobs
scheduler = APScheduler()

@scheduler.task('cron', id="update_movies", hour='*', minute='*/15')
def update_movies():
    """Updates the movies cache hourly."""
    try:
        # get the users
        users = db.collection('users').stream()
        for user in users:
            user_data = user.to_dict()
            # build users movie list
            movie_list = Account(
                token=secrets.tmdb_token,
                session_id=user_data["tmdb_session"],
                # blocklist=fsWatchGroup.get_user_blocklist(member=user.id),
                # m2w_id=user.id,
                # m2w_nick=user_data["nickname"],
                **user_data["tmdb_user"]
            ).get_watchlist_movie()
            # check and update cache
            for movie in movie_list:
                mov = Movie(
                    id_=movie['id'],
                    token=secrets.tmdb_token,
                    db=db
                )
    except:
        pass


#setting up requests and endpoints
@app.route("/", methods=['POST', 'GET'])
def root():
    if 'user' in session:
        logged_on = session['user']
        user_ref = db.collection("users").document(logged_on)
        user_data = user_ref.get().to_dict()
        group = user_data["primary_group"]
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
        # session.pop("user")
    except KeyError:
        return redirect("/")
    else:
        return redirect("/")


@app.route("/login", methods=['POST', 'GET'])
def login():
    target = request.args.get("redirect", default="/")
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = firebase_auth.sign_in_with_email_and_password(
                email=email,
                password=password
            )
            session['user'] = user['localId']
            session['email'] = user['email']
            session['nickname'] = user['displayName']
            session['idToken'] = user['idToken']
            session['refreshToken'] = user['refreshToken']
            session['expiresIn'] = user['expiresIn']

            user_info = firebase_auth.get_account_info(user['idToken'])
            session['emailVerified'] = user_info['users'][0]['emailVerified']
            session['lastRefreshAt'] = user_info['users'][0]['lastRefreshAt']
            session['nextRefreshAt'] = datetime.fromisoformat(session['lastRefreshAt']) + timedelta(seconds=int(int(session['expiresIn'])*0.9))

            session['approve_id'] = None

            user_data = db.collection("users").document(session['user']).get().to_dict()
            if user_data['tmdb_session'] is not None:
                try:
                    fresh_data = tmdb_auth.get_account_data(session_id=user_data['tmdb_session'])
                except:
                    pass
                else:
                    data = {
                        "tmdb_user":fresh_data
                    }
                    db.collection("users").document(session['user']).set(
                        data,
                        merge=True
                    )
        except HTTPError as he:
            msg = get_firebase_error(he)
            return render_template("login.html", error=msg, target=target)
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
        email = request.form.get('email')
        email_2 = request.form.get('email_confirm')
        password = request.form.get('password')
        password_2 = request.form.get('password_confirm')
        nickname = request.form.get('nickname')
        if email != email_2:
            return render_template(
                "signup.html", 
                error="Emails don't match!",
                email=email,
                email_c=email_2,
                password=password,
                password_c=password_2,
                nickname=nickname
                )
        elif password != password_2:
            return render_template(
                "signup.html", 
                error="Passwords don't match!",
                email=email,
                email_c=email_2,
                nickname=nickname
                )
        else:
            if nickname == '':
                nickname = email.split('@')[0]
            try:
                my_user = firebase_auth.create_user_with_email_and_password(
                    email=email,
                    password=password
                )
                firebase_auth.update_profile(
                    id_token=my_user['idToken'],
                    display_name=nickname)
                firebase_auth.send_email_verification(my_user['idToken'])
                
                data = {
                    "email": email, 
                    "nickname": nickname, 
                    "tmdb_user": None,
                    "tmdb_session": None,
                    "locale": "HU",
                    "primary_group": None
                    }
                db.collection("users").document(my_user['localId']).set(data)
            except HTTPError as he:
                msg = get_firebase_error(he)
                return render_template(
                    "signup.html", 
                    error=msg,
                    email=email,
                    email_c=email_2,
                    password=password,
                    password_c=password_2,
                    nickname=request.form.get('nickname')
                    )
            except Exception as e:
                return render_template(
                    "signup.html", 
                    error=e,
                    email=email,
                    email_c=email_2,
                    password=password,
                    password_c=password_2,
                    nickname=request.form.get('nickname')
                    )
            else:
                return render_template("signup.html", success=True)
    else:
        return render_template("signup.html")


@app.route("/approved/<approve_id>")
def approved(approve_id):
    approval = request.args.get("approved")
    request_token = request.args.get("request_token")
    try:
        if (approve_id == session['approve_id']) and (approval == "true"):
            try:
                payload = json.loads(session['request_payload'])
                tmdb_session = tmdb_auth.create_session_id(payload=payload)
                user_data = tmdb_auth.get_account_data(tmdb_session)
                db.collection("users").document(session['user']).set(
                    {"tmdb_session": tmdb_session, "tmdb_user": user_data}, 
                    merge=True
                    )
            except Exception as err:
                return render_template("approved.html", success=False, error=err)
            else:
                return render_template("approved.html", success=True)
        else:
            return render_template("approved.html", success=False, error="Session not approved or invalid.")
    except Exception:
        return redirect(url_for('login'))


@app.route("/profile")
def profile():
    if "user" in session:
        user_ref = db.collection("users").document(session['user'])
        user_data = user_ref.get()
        return render_template('profile.html', profile_data=user_data.to_dict(), logged_on=session['user'])
    else:
        return redirect("/login?redirect=/profile")
    
@app.route("/link-to-tmdb")
def link_to_tmdb():
    if 'user' in session:
        try:
            response = tmdb_auth.create_request_token()
            session['request_payload'] = json.dumps(response)
            # print(session['request_payload'])
            ask_URL = tmdb_auth.ask_user_permission()
            session['approve_id'] = tmdb_auth.approve_id
        except Exception:
            return "Something went wrong!"
        else:
            return redirect(ask_URL)
    else:
        return redirect("/login?redirect=/link-to-tmdb")
    

@app.route("/resend-verification")
def resend_verification():
    if 'user' in session:
        if session['emailVerified'] == False:
            try:
                firebase_auth.send_email_verification(id_token=session['idToken'])
            except Exception as e:
                flash(f"The following error occured: {e}")
            else:
                flash("Please check your mailbox you should receive a verification email shortly!")
            return redirect("/")
        else:
            return redirect("/")
    else:
        return redirect("/login?redirect=/resend-verification")
    
@app.route("/api/group/<group>")
def group_content(group):
    if 'user' in session:
        logged_on = session['user']
        w_group = fsWatchGroup(
            id=group,
            database=db,
            tmdb_token=secrets.tmdb_token,
            primary_member=logged_on
        )
        movie_watchlist = w_group.get_movie_grouplist_union()
        display = {}
        for movie in movie_watchlist:
            mov = Movie(
                id_=movie['id'],
                token=secrets.tmdb_token,
                db=db
            )
            display[mov.id] = mov.get_datasheet_for_locale(locale=w_group.locale)
            votes = {}
            for key, value in movie['votes'].items():
                member = w_group.get_member(key)
                if key == logged_on:
                    display[mov.id]['your_vote'] = value
                else:
                    votes[key] = {
                        "nickname": member.m2w_nick,
                        "email": member.m2w_email,
                        "vote": value
                    }
            display[mov.id]['votes'] = votes
        print(display[787699]['votes'])
        return render_template("group_content.html", movies=display)
    else:
        target = f"/login?redirect=/api/group/{group}"
        return redirect(target)
    
@app.route("/api/vote/<movie>/<vote>")
def vote_for_movie(movie, vote):
    if 'user' in session:
        logged_on = session['user']
        user_data = db.collection('users').document(logged_on).get().to_dict()
        user = Account(
            token=secrets.tmdb_token,
            session_id=user_data["tmdb_session"],
            **user_data["tmdb_user"],
            m2w_email=user_data["email"],
            m2w_id=logged_on,
            m2w_nick=user_data["nickname"]
        )
        if vote == "like":
            user.add_movie_to_watchlist(int(movie))
            remove_from_blocklist(
                db=db,
                member=logged_on,
                movie_id=movie
                )
            # return f"liking {movie}"
            return render_template("vote_response.html", vote="liked", movie_id=movie)
        elif vote == "block":
            user.remove_movie_from_watchlist(int(movie))
            add_to_blocklist(
                db=db,
                member=logged_on,
                movie_id=movie
            )
            # return f"blocking {movie}"
            return render_template("vote_response.html", vote="blocked", movie_id=movie)
    else:
        target = f"/login?redirect=/api/vote/{movie}/{vote}"
        return redirect(target)

#starting scheduler    
scheduler.init_app(app)
scheduler.start()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
