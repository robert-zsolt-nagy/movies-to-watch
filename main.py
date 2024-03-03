from flask import Flask, render_template, session, redirect, request
import firebase_admin
from firebase_admin import credentials
from src.authenticate import SecretManager
import pyrebase
from requests.exceptions import HTTPError
import json

# reading the secrets
secrets = SecretManager()

# setting up firebase authentication
# cred = credentials.Certificate(secrets.firebase_cert)
# firebase_admin.initialize_app(cred)
# firebase_app = pyrebase.initialize_app(config=secrets.firebase_config)
# firebase_auth = firebase_app.auth()

# my_user = firebase_auth.create_user_with_email_and_password(
#     email=secrets.secrets['user']['email'],
#     password=secrets.secrets['user']['m2w_password']
# )

# firebase_auth.send_email_verification(id_token=secrets.secrets['user']['id_token'])
# my_user = firebase_auth.sign_in_with_email_and_password(
#     email=secrets.secrets['user']['email'],
#     password=secrets.secrets['user']['m2w_password']
# )
# info = firebase_auth.get_account_info(my_user['id_token'])
# print(info)



# setting up Flask
app = Flask(__name__)
app.secret_key = secrets.secrets['flask']['secret_key']

firebase_app = pyrebase.initialize_app(config=secrets.firebase_config)
firebase_auth = firebase_app.auth()

@app.route("/", methods=['POST', 'GET'])
def root():
    if 'user' in session:
        logged_on = session['user']
        info = session['info']
        return render_template("index.html", user_data=logged_on, info=info)
    else:
        return render_template("index.html")
        # return redirect("/login")
    # if request.method == 'POST':
    #     email = request.form.get('email')
    #     password = request.form.get('password')
    #     try:
    #         user = firebase_auth.sign_in_with_email_and_password(
    #             email=email,
    #             password=password
    #         )
    #         session['user'] = email
    #         session['info'] = firebase_auth.get_account_info(user['idToken'])
    #     except:
    #         return "Failed to log in."
    # return render_template("index.html")
        
@app.route("/logout")
def logout():
    try:
        session.pop('user')
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
            session['info'] = firebase_auth.get_account_info(user['idToken'])
        except HTTPError as he:
            he_error = json.loads(he.args[1])
            he_error = he_error['error']["message"]
            return render_template("login.html", error=he_error)
        except Exception as e:
            return render_template("login.html", error=e)
        else:
            return redirect("/")
    else:
        return render_template("login.html")
    
@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            my_user = firebase_auth.create_user_with_email_and_password(
                email=email,
                password=password
            )
        except HTTPError as he:
            # he_error = json.loads(he.args[1])
            # he_error = he_error['error']["message"]
            he_error = he
            return render_template("signup.html", error=he_error)
        except Exception as e:
            return render_template("signup.html", error=e)
        else:
            return render_template("signup.html", success=True)
    else:
        return render_template("signup.html")


if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)