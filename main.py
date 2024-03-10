from flask import Flask, render_template, session, redirect, request, flash, url_for
import firebase_admin
from firebase_admin import credentials
from src.authenticate import SecretManager, Authentication
import pyrebase
from requests.exceptions import HTTPError
import json
from google.cloud import firestore
from datetime import datetime, timedelta

# reading the secrets
secrets = SecretManager()

# conenct to database
db = firestore.Client(project=secrets.secrets['firestore']['project'])

# setting upo tmdb
tmdb_auth = Authentication(secrets=secrets.secrets)

def get_firebase_error(error: HTTPError) -> str:
    """Get the error message from a raised error. """
    message = json.loads(error.args[1])
    return message['error']["message"]

# setting up Flask
app = Flask(__name__)
app.secret_key = secrets.secrets['flask']['secret_key']

firebase_app = pyrebase.initialize_app(config=secrets.firebase_config)
firebase_auth = firebase_app.auth()

@app.route("/", methods=['POST', 'GET'])
def root():
    if 'user' in session:
        logged_on = session['user']
        # info = session['info']
        # info = session['user_str']
        return render_template("index.html", user_data=logged_on, session=session)
    else:
        # return render_template("index.html")
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
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = firebase_auth.sign_in_with_email_and_password(
                email=email,
                password=password
            )
            session['user'] = email
            session['idToken'] = user['idToken']
            session['refreshToken'] = user['refreshToken']
            session['expiresIn'] = user['expiresIn']

            user_info = firebase_auth.get_account_info(user['idToken'])
            session['emailVerified'] = user_info['users'][0]['emailVerified']
            session['lastRefreshAt'] = user_info['users'][0]['lastRefreshAt']
            session['nextRefreshAt'] = datetime.fromisoformat(session['lastRefreshAt']) + timedelta(seconds=int(int(session['expiresIn'])*0.9))

            session['approve_id'] = None
        except HTTPError as he:
            msg = get_firebase_error(he)
            return render_template("login.html", error=msg)
        except Exception as e:
            return render_template("login.html", error=e)
        else:
            return redirect("/")
    else:
        if 'user' in session:
            return redirect("/")
        else:
            return render_template("login.html")


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
                    "tmdb_session": None
                    }
                db.collection("users").document(email).set(data)
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
                    {"tmdb_session": tmdb_session, "tmdb_user": user_data['username']}, 
                    merge=True
                    )
            except:
                return render_template("approved.html", success=False)
            else:
                return render_template("approved.html", success=True)
        else:
            return render_template("approved.html", success=False)
    except Exception:
        return redirect(url_for('login'))


@app.route("/profile")
def profile():
    if "user" in session:
        user_ref = db.collection("users").document(session['user'])
        user_data = user_ref.get()
        return render_template('profile.html', profile_data=user_data.to_dict())
    else:
        return redirect(url_for('login'))
    
@app.route("/link-to-tmdb")
def link_to_tmdb():
    if 'user' in session:
        try:
            response = tmdb_auth.create_request_token()
            session['request_payload'] = json.dumps(response)
            print(session['request_payload'])
            ask_URL = tmdb_auth.ask_user_permission()
            session['approve_id'] = tmdb_auth.approve_id
        except Exception:
            return "Something wnet wrong!"
        else:
            return redirect(ask_URL)
    else:
        return redirect(url_for('login'))


if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)