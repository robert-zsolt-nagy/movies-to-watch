import json
import logging
import os
import time
import uuid
from typing import Optional

import psutil
import pyrebase
import requests
from flask import Flask, render_template, session, redirect, request, flash, Response
from flask_apscheduler import APScheduler
from neo4j import Driver, GraphDatabase
from opentelemetry import metrics, _logs
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from src.dao.authentication_manager import AuthenticationManager, FirebaseAuthenticationManager, AuthException
from src.dao.m2w_graph_db_repository_auth import Neo4jAuthenticationManager
from src.dao.secret_manager import SecretManager
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.tmdb_user_repository import TmdbUserRepository, TmdbRequestToken
from src.services.group_service import GroupManagerService
from src.services.m2w_dtos import VoteValueDto
from src.services.movie_caching import MovieCachingService
from src.services.user_service import UserManagerService, WeakPasswordError, EmailMismatchError, PasswordMismatchError

# logging level #
logging.basicConfig(level=logging.INFO)
process_started_at = time.time()
neo4j_log = logging.getLogger("neo4j")
neo4j_log.setLevel(logging.WARNING)

# OpenTelemetry Settings #
if os.getenv("MoviesToWatch") == "test":
    environ = "local"
else:
    environ = "prod"
OTEL_RESOURCE_ATTRIBUTES = {
    "service.instance.id": str(uuid.uuid1()),
    "environment": environ
}

# OTEL Metrics #
# Initialize metering and an exporter that can send data to an OTLP endpoint
if environ != "local":
    metrics.set_meter_provider(
        MeterProvider(
            resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES),
            metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())]
        )
    )
else:
    metrics.set_meter_provider(
        MeterProvider(
            resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES)
        )
    )
metrics.get_meter_provider()
tmdb_http_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="tmdb.http.duration",
    description="measures the duration of the HTTP request to TMDB",
    unit="ms"
)
m2w_database_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="m2w.firestore.duration",
    description="measures the duration of a request to M2W firestore database.",
    unit="ms"
)
system_uptime_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="service.uptime",
    description="measures the uptime of the current instance.",
    unit="sec"
)
process_uptime_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="service.process.uptime",
    description="measures the uptime of the current python process.",
    unit="sec"
)
cpu_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="service.cpu",
    description="measures CPU usage of the current python process.",
    unit="percent"
)
memory_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="service.memory",
    description="measures memory usage of the current python process.",
    unit="percent"
)
endpoint_recorder = metrics.get_meter("opentelemetry.instrumentation.custom").create_histogram(
    name="http.endpoint.request.duration",
    description="measures the duration of a request measured at the HTTP endpoint.",
    unit="sec"
)
# logout_counter = metrics.get_meter("opentelemetry.instrumentation.custom").create_counter(
#     "logout.invocations", 
#     unit="1", 
#     description="Measures the number of times the logout method is invoked."
#     )

# Logs #
# Initialize logging and an exporter that can send data to an OTLP endpoint by attaching OTLP handler to root logger
if environ != "local":
    _logs.set_logger_provider(LoggerProvider(resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES)))
    logging.getLogger().addHandler(
        LoggingHandler(
            logger_provider=_logs.get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        )
    )

# reading the secrets
if os.getenv("MoviesToWatch") == "test":
    SECRETS = SecretManager('secrets_test.toml')
else:
    SECRETS = SecretManager('secrets.toml')

# connect to database
def connect_to_neo4j() -> Driver:
    """ Returns a properly set-up Driver instance. """
    uri = SECRETS.neo4j_uri
    auth = (SECRETS.neo4j_user, SECRETS.neo4j_pass)

    driver = GraphDatabase.driver(uri=uri, auth=auth)
    driver.verify_connectivity()
    return driver

db_driver = connect_to_neo4j()

# define helper functions
def get_tmdb_http_client(session_: Optional[requests.Session] = None) -> TmdbHttpClient:
    """ Returns a properly set up TmdbHttpClient instance with the specified session."""
    return TmdbHttpClient(
        token=SECRETS.tmdb_token,
        base_url=SECRETS.tmdb_api,
        session=session_,
        histogram=tmdb_http_recorder
    )



def get_group_service(user_service: UserManagerService) -> GroupManagerService:
    return GroupManagerService(
        secrets=SECRETS,
        db=db_driver,
        user_service=user_service
    )


def get_movie_service() -> MovieCachingService:
    return MovieCachingService(
        tmdb_http_client=get_tmdb_http_client(),
        db=db_driver
    )


def get_user_service() -> UserManagerService:
    return UserManagerService(
        db=db_driver,
        auth=get_auth(),
        user_repo=TmdbUserRepository(
            tmdb_http_client=get_tmdb_http_client()
        )
    )

def get_auth() -> AuthenticationManager:
    """ Returns a properly configured instance of AuthenticationManager. """
    if SECRETS.auth_store != "neo4j":
        return FirebaseAuthenticationManager(config=SECRETS.firebase_config)
    else:
        return Neo4jAuthenticationManager(driver=db_driver)


def prepare_profiles(profile_pic: str) -> list:
    """ Prepares a list of valid profile picture configurations for the profile page. """
    result = []
    for ix in range(42):
        temp = ix + 1
        if temp < 10:
            ix_str = f'0{temp}'
        else:
            ix_str = str(temp)
        elem = {
            "id": f"img-{ix_str}",
            "value": f"{ix_str}.png",
            "checked": False
        }
        if elem['value'] == profile_pic:
            elem["checked"] = True
        result.append(elem)
    return result


# setting up Flask
app = Flask(__name__)
app.secret_key = SECRETS.flask_key
FlaskInstrumentor().instrument_app(app)

firebase_app = None
firebase_auth = None
if SECRETS.auth_store != "neo4j":
    # setting up firebase authentication
    firebase_app = pyrebase.initialize_app(config=SECRETS.firebase_config)
    firebase_auth = firebase_app.auth()

#################################
# setting up scheduler and jobs #
#################################
scheduler = APScheduler()


@scheduler.task('cron', id="report_uptime", hour='*', minute='*/1')
def report_system_uptime():
    """Reports the system uptime of the instance."""
    if environ != "local":
        system_uptime = time.monotonic()
        system_uptime_recorder.record(amount=system_uptime, attributes={"pid": os.getpid()})
        process_uptime = time.time() - process_started_at
        process_uptime_recorder.record(amount=process_uptime, attributes={"pid": os.getpid()})
        cpu_percent = psutil.cpu_percent()
        cpu_recorder.record(amount=cpu_percent, attributes={"pid": os.getpid()})
        used_ram_percent = psutil.virtual_memory().percent
        memory_recorder.record(amount=used_ram_percent, attributes={"pid": os.getpid()})


def report_call(start: float, method: str, endpoint: str, outcome: str):
    """ Records the telemetry data to the histogram attribute. """
    duration = time.time() - start
    endpoint_recorder.record(amount=duration, attributes={
        "method": method,
        "endpoint": endpoint,
        "status": outcome
    })


#####################################
# setting up requests and endpoints #
#####################################
@app.route("/error")
def error():
    report_call(start=time.time(), method=request.method, endpoint=request.endpoint, outcome="success")
    return render_template('error.html')


@app.route("/", methods=['POST', 'GET'])
def root():
    start = time.time()
    if 'user' in session:
        try:
            logged_on = session['user']
            user_service = get_user_service()
            group_service = get_group_service(user_service=user_service)
            group = group_service.get_primary_group_for_m2w_user(user_id=logged_on)
            user_data = user_service.get_m2w_user_profile_data(user_id=logged_on)
        except Exception as e:
            logging.error(f"Error by gathering content for index page: {e}")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template("error.html", error=e)
        else:
            logging.debug("Rendering index page.")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return render_template(
                "index.html",
                logged_on=session['nickname'],
                verified=session['emailVerified'],
                tmdb_linked=user_data.tmdb_user.session if user_data.tmdb_user else None,
                group=group
            )
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login")


@app.route("/logout")
def logout():
    start = time.time()
    try:
        keys = list(session.keys())
        for key in keys:
            session.pop(key)
    except KeyError:
        # logout_counter.add(1, {"logout.valid.n": "false"})
        logging.error("Error during logout.")
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
        return redirect("/")
    else:
        # logout_counter.add(1, {"logout.valid.n": "true"})
        logging.debug("Successful logout.")
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
        return redirect("/")


@app.route("/login", methods=['POST', 'GET'])
def login():
    start = time.time()
    logging.debug(f"Login page requested. Method: {request.method}")
    target = request.args.get("redirect", default="/")
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            user_service = get_user_service()
            user = user_service.sign_in_and_update_tmdb_cache(email=email, password=password)
            for k, v in user.items():
                session[k] = v
        except Exception as e:
            logging.error(f"Error during logging in: {e}")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template("login.html", error=e, target=target)
        else:
            logging.debug("Successful logon.")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return redirect(target)
    else:
        if 'user' in session:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="already_logged_in")
            return redirect(target)
        else:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return render_template("login.html", target=target)


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    start = time.time()
    if request.method == 'POST':
        email = ""
        confirm_email = ""
        password = ""
        confirm_password = ""
        nickname = ""
        try:
            email = request.form.get('email')
            confirm_email = request.form.get('email_confirm')
            password = request.form.get('password')
            confirm_password = request.form.get('password_confirm')
            nickname = request.form.get('nickname')
            picture = request.form.get('profile_image', "01.png")
            locale = "HU"
            if nickname == '':
                nickname = email.split('@')[0]
            user_service = get_user_service()
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
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="email_mismatch_error")
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
            report_call(start=start, method=request.method, endpoint=request.endpoint,
                        outcome="password_mismatch_error")
            return render_template(
                "signup.html",
                error="Passwords don't match!",
                email=email,
                email_c=confirm_email,
                nickname=nickname
            )
        except WeakPasswordError:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="weak_password_error")
            return render_template(
                "signup.html",
                error="Password must contain at least 6 characters!",
                email=email,
                email_c=confirm_email,
                nickname=nickname
            )
        except AuthException as e:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="http_error")
            return render_template(
                "signup.html",
                error=e,
                email=email,
                email_c=confirm_email,
                password=password,
                password_c=confirm_password,
                nickname=nickname
            )
        except Exception as e:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
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
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return render_template("signup.html", success=response)
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
        return render_template("signup.html")


@app.route("/approved")
def approved():
    start = time.time()
    approval = request.args.get("approved")
    request_token = request.args.get("request_token")
    try:
        token_from_session = None
        if session['tmdb_request_token'] is not None:
            token_from_session = TmdbRequestToken.from_response(json.loads(session['tmdb_request_token']))
        if (token_from_session is not None) and (request_token == token_from_session.request_token) and (approval == "true"):
            try:
                user_service = get_user_service()
                user_service.create_tmdb_session_for_user(user_id=session['user'], request_token=token_from_session)
            except Exception as err:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="approve_error")
                return render_template("approved.html", success=False, error=err)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                return render_template("approved.html", success=True)
        else:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="invalid_session")
            return render_template("approved.html", success=False, error="Session not approved or invalid.")
    except Exception as err:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="generic_error")
        return render_template("error.html", error=err)


@app.route("/profile", methods=['POST', 'GET'])
def profile():
    start = time.time()
    if "user" in session:
        logged_on = session['user']
        if request.method == 'GET':
            try:
                user_service = get_user_service()
                user_data = user_service.get_m2w_user_profile_data(user_id=session['user'])
                profile_pics = prepare_profiles(profile_pic=user_data.profile_pic)
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return render_template('error.html', error=e)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                return render_template('profile.html', profile_data=user_data, logged_on=session['user'],
                                       profile_pics=profile_pics)
        elif request.method == 'POST':
            try:
                user_service = get_user_service()
                new_profile_pic = request.form.get("profile_image")
                old_profile_pic = request.form.get("current_profile_pic")
                if new_profile_pic != old_profile_pic:
                    user_service.update_profile_picture(user_id=logged_on, profile_pic=new_profile_pic)
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return render_template('error.html', error=e)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                flash("Changes saved!")
                return redirect("/profile")
        else:
            # this should never happen because the method is checked
            return None
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login?redirect=/profile")


@app.route("/link-to-tmdb")
def link_to_tmdb():
    start = time.time()
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            user_service = get_user_service()
            token = user_service.get_tmdb_request_token()
            permission_url = user_service.get_tmdb_permission_url(
                tmdb_request_token=token,
                redirect_to=f'{SECRETS.m2w_base_url}/approved',
                tmdb_url=SECRETS.tmdb_home
            )
            session['tmdb_request_token'] = json.dumps(token.to_dict())
            permission_url = permission_url
        except Exception as e:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template('error.html', error=e)
        else:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return redirect(permission_url)
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login?redirect=/link-to-tmdb")


@app.route("/resend-verification")
def resend_verification():
    start = time.time()
    if 'user' in session:
        if not session['emailVerified']:
            try:
                user_service = get_user_service()
                account_data = user_service.get_firebase_user_account_info(user_id_token=session['idToken'])
                if account_data.email_verified:
                    session['emailVerified'] = account_data.email_verified
                else:
                    firebase_auth.send_email_verification(id_token=session['idToken'])
            except Exception as e:
                flash(f"The following error occurred: {e}")
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                redirect('/error')
            else:
                status = "success"
                if account_data.email_verified:
                    flash("Your email verification is already complete!")
                else:
                    flash("Please check your mailbox you should receive a verification email shortly!")
                    status = "already_complete"
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome=status)
            return redirect('/error')
        else:
            flash("Your email verification is already complete!")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="already_complete")
            return redirect('/error')
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login?redirect=/resend-verification")


@app.route("/api/group/<group>")
def group_content(group):
    start = time.time()
    logging.debug(f"Calling /api/group/{group}")
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            logging.debug(f"Setting up objects for /api/group/{group}")
            logged_on = session['user']
            user_service = get_user_service()
            group_service = get_group_service(user_service=user_service)
            logging.debug(f"Gathering data for /api/group/{group}")
            movie_datasheets = group_service.get_group_content(
                group_id=uuid.UUID(hex=group),
                current_user_id=logged_on
            )
        except Exception as e:
            flash(f"The following error occurred: {e}")
            logging.error(f"Error by preparing group data. {e}")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template("group_content.html", error=True)
        else:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            logging.debug(f"Rendering group content for /api/group/{group}")
            return render_template("group_content.html", movies=movie_datasheets, group=group)
        finally:
            logging.debug(f"Group content for /api/group/{group} ready.")
    else:
        flash("You are not logged in!")
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="not_logged_in")
        return render_template("group_content.html", error=True)


@app.route("/api/vote/<movie>/<vote>")
def vote_for_movie(movie, vote):
    start = time.time()
    if ('user' in session) and (session['emailVerified'] == True):
        try:
            logged_on = session['user']
            user_service = get_user_service()
            group_service = get_group_service(user_service=user_service)
            response = group_service.vote_for_movie_by_user(
                movie_id=int(movie),
                user_id=logged_on,
                vote=VoteValueDto.from_request(vote)
            )
        except Exception as e:
            logging.error(f"Error during vote for movie {movie}. {e}")
            flash(f"The following error occurred: {e}")
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template("vote_response.html", vote=vote, movie_id=movie, error=True)
        else:
            if response:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                return render_template("vote_response.html", vote=vote, movie_id=movie)
            else:
                flash("Unable to register vote.")
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="failed")
                return render_template("vote_response.html", vote=vote, movie_id=movie, error=True)
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        target = f"/login?redirect=/api/vote/{movie}/{vote}"
        return redirect(target)


@app.route("/api/watched/<movie>/<group_id>", methods=['POST', 'GET'])
def watched_movie(movie, group_id):
    start = time.time()
    if ('user' in session) and (session['emailVerified'] == True):
        if request.method == 'GET':
            try:
                movie_service = get_movie_service()
                title = movie_service.get_movie_title(movie_id=int(movie))
            except Exception as e:
                logging.error(f"Error during vote for movie {movie}. {e}")
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                flash(f"The following error occurred: {e}")
                return redirect(location="/error")
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                return render_template('watched_movie.html', movie=movie,
                                       group_id=group_id, movie_title=title)
        if request.method == 'POST':
            watch_mode = request.form.get('watch_mode')
            try:
                logged_on = session['user']
                user_service = get_user_service()
                movie_service = get_movie_service()
                group_service = get_group_service(user_service=user_service)
                title = movie_service.get_movie_title(movie_id=int(movie))
                if watch_mode == 'alone':
                    group_service.watch_movie_by_user(movie_id=int(movie), user_id=logged_on)
                else:
                    group_service.watch_movie_by_group(movie_id=int(movie), user_id=logged_on, group_id=uuid.UUID(hex=group_id))
            except Exception as e:
                logging.error(f"Error during vote for movie {movie}. {e}")
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                flash(f"The following error occurred: {e}")
                return redirect("/error")
            else:
                if watch_mode == 'alone':
                    flash(f"You watched: {title}")
                    report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success_alone")
                    return redirect("/")
                else:
                    flash(f"Your Group watched: {title}")
                    report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success_group")
                    return redirect("/")

@app.route("/api/refresh-cache", methods=['GET'])
def refresh_movie_cache():
    """Updates the movie cache regularly."""
    api_token = request.headers.get(key="X-M2W-API-Token")
    if api_token is None:
        logging.error("API token is missing.")
        resp = Response(response="API Token is missing.", status=401)
        resp.headers["Content-Type"] = "application/json"
        return resp
    try:
        logging.info("Movie cache update started.")
        if not get_movie_service().movie_cache_update_job(api_token=api_token):
            logging.error("Movie cache update was not necessary.")
            raise Exception("Movie cache update was not necessary.")
    except AuthException:
        logging.error("API token is invalid.")
        resp = Response(response="API Token is invalid.", status=401)
        resp.headers["Content-Type"] = "application/json"
        return resp
    except Exception as e:
        logging.error(f"Movie cache error: {e}")
        resp = Response(response=f"Movie cache error: {e}", status=500)
        resp.headers["Content-Type"] = "application/json"
        return resp
    else:
        logging.info("Movie cache update finished.")
        resp = Response(response=None, status=200)
        resp.headers["Content-Type"] = "application/json"
        return resp

# starting scheduler
if os.getenv("MoviesToWatch") != "test":
    scheduler.init_app(app)
    scheduler.start()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
