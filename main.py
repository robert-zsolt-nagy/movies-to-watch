import json
from typing import Optional
import psutil
import os
import time
import uuid
import logging
import requests
from requests.exceptions import HTTPError
from expiringdict import ExpiringDict

import pyrebase
from flask import Flask, render_template, session, redirect, request, flash
from flask_apscheduler import APScheduler
from google.oauth2 import service_account

from src.dao.secret_manager import SecretManager
from src.dao.tmdb_http_client import TmdbHttpClient
from src.dao.m2w_database import M2WDatabase
from src.dao.authentication_manager import AuthenticationManager
from src.dao.tmdb_user_repository import TmdbUserRepository

from src.services.movie_caching import MovieCachingService
from src.services.user_service import UserManagerService, WeakPasswordError, EmailMismatchError, PasswordMismatchError
from src.services.group_service import GroupManagerService

from opentelemetry.sdk.resources import Resource
from opentelemetry import metrics, _logs
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# logging level #
logging.basicConfig(level=logging.INFO)
process_started_at = time.time()

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
metrics.set_meter_provider(
    MeterProvider(
        resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES),
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())]
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

# set up in memory cache
movie_item_cache = ExpiringDict(max_len=200, max_age_seconds=SECRETS.m2w_movie_retention)

# connect to database
m2w_db_cert = service_account.Credentials.from_service_account_file(SECRETS.firestore_cert)


# define helper functions
def get_tmdb_http_client(session_: Optional[requests.Session] = None) -> TmdbHttpClient:
    """ Returns a properly set up TmdbHttpClient instance with the specified session."""
    return TmdbHttpClient(
        token=SECRETS.tmdb_token,
        base_url=SECRETS.tmdb_API,
        session=session_,
        histogram=tmdb_http_recorder
    )


def get_m2w_db() -> M2WDatabase:
    """ Returns a properly set up M2WDatabase instance. """
    return M2WDatabase(
        project=SECRETS.firestore_project,
        credentials=m2w_db_cert,
        histogram=m2w_database_recorder
    )


def get_auth() -> AuthenticationManager:
    """ Returns a properly set up instance of AuthenticationManager. """
    return AuthenticationManager(
        config=SECRETS.firebase_config
    )


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

# setting up firebase authentication
firebase_app = pyrebase.initialize_app(config=SECRETS.firebase_config)
firebase_auth = firebase_app.auth()

#################################
# setting up scheduler and jobs #
#################################
scheduler = APScheduler()


@scheduler.task('cron', id="update_movies", hour='*', minute='*/15')
def update_movie_cache():
    """Updates the movies cache regularly."""
    try:
        logging.info("Movie cache update started.")
        MovieCachingService(
            tmdb_http_client=get_tmdb_http_client(),
            m2w_database=get_m2w_db(),
            m2w_movie_retention=SECRETS.m2w_movie_retention,
            cache=movie_item_cache
            ).movie_cache_update_job()
    except Exception as e:
        logging.error(f"Movie cache error: {e}")
    else:
        logging.info("Movie cache update finished.")


@scheduler.task('cron', id="report_uptime", hour='*', minute='*/1')
def report_system_uptime():
    """Reports the system uptime of the instance."""
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
                tmdb_linked=user_data['tmdb_session'],
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
        except HTTPError as he:
            msg = AuthenticationManager.get_authentication_error_msg(he)
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="http_error")
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
                user_service = UserManagerService(
                    m2w_db=get_m2w_db(),
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=get_tmdb_http_client()
                    )
                )
                user_data = user_service.get_m2w_user_profile_data(user_id=session['user'])
                profile_pics = prepare_profiles(profile_pic=user_data.get('profile_pic', ''))
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return render_template('error.html', error=e)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                return render_template('profile.html', profile_data=user_data, logged_on=session['user'], profile_pics=profile_pics)
        elif request.method == 'POST':
            try:
                user_service = UserManagerService(
                    m2w_db=get_m2w_db(),
                    auth=get_auth(),
                    user_repo=TmdbUserRepository(
                        tmdb_http_client=get_tmdb_http_client()
                    )
                )
                new_profile_pic = request.form.get("profile_image")
                old_profile_pic = request.form.get("current_profile_pic")
                if new_profile_pic != old_profile_pic:
                    user_service.update_user_data(user_id=logged_on, user_data={"profile_pic": new_profile_pic})
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return render_template('error.html', error=e)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
                flash("Changes saved!")
                return redirect("/profile")
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login?redirect=/profile")


@app.route("/link-to-tmdb")
def link_to_tmdb():
    start = time.time()
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
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
            return render_template('error.html', error=e)
        else:
            report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
            return redirect(permission_URL)
    else:
        report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="redirect_to_login")
        return redirect("/login?redirect=/link-to-tmdb")


@app.route("/resend-verification")
def resend_verification():
    start = time.time()
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
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                redirect('/error')
            else:
                status = "success"
                if account_data['emailVerified']:
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
                    m2w_movie_retention=SECRETS.m2w_movie_retention,
                    cache=movie_item_cache
                )
            )
            logging.debug(f"Gathering data for /api/group/{group}")
            movie_datasheets = group_service.get_group_content(
                group_id=group,
                primary_user=logged_on
            )
        except Exception as e:
            flash("The following error occured:")
            flash(e)
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
                    m2w_movie_retention=SECRETS.m2w_movie_retention,
                    cache=movie_item_cache
                )
            )
            response = group_service.vote_for_movie_by_user(
                movie_id=movie,
                user_id=logged_on,
                vote=vote
            )
        except Exception as e:
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
                movie_service = MovieCachingService(
                    tmdb_http_client=get_tmdb_http_client(),
                    m2w_database=get_m2w_db(),
                    m2w_movie_retention=SECRETS.m2w_movie_retention,
                    cache=movie_item_cache
                )
                movie_data = movie_service.get_movie_details(movie_id=movie)
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return redirect("/error", error=e)
            else:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success")
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
                        m2w_movie_retention=SECRETS.m2w_movie_retention,
                        cache=movie_item_cache
                    )
                )
                movie_data = group_service.movie.get_movie_details(movie_id=movie)
                if watchmode == 'alone':
                    group_service.watch_movie_by_user(movie_id=movie, user_id=logged_on)
                else:
                    group_service.watch_movie_by_group(movie_id=movie, group_id=group_id)
            except Exception as e:
                report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="error")
                return redirect("/error", error=e)
            else:
                if watchmode == 'alone':
                    flash(f"You watched: {movie_data['title']}")
                    report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success_alone")
                    return redirect("/")
                else:
                    flash(f"Your Group watched: {movie_data['title']}")
                    report_call(start=start, method=request.method, endpoint=request.endpoint, outcome="success_group")
                    return redirect("/")


# starting scheduler
if os.getenv("MoviesToWatch") != "test":
    scheduler.init_app(app)
    scheduler.start()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
