import os
import sys
import time
import json
import logging
import logging.handlers
from colorlog import ColoredFormatter
from flask import Flask, render_template, request, session, g
from flask_restful import Api
from flask_cors import CORS
from jinja2.exceptions import TemplateNotFound
from database.database import Database
from core_lib.utils.global_config import Config
from core_lib.utils.username_filter import UsernameFilter

from resources.smart_tricks import askfor
def get_userinfo():
    """Retrieve user info to store in client session"""
    uptime = askfor.get('api/system/uptime').json().get('response').get('uptime')
    session_uptime = session.get('time') if session.get('time') else 1
    time_now = int(time.time())
    uptime = time_now - uptime

    # Refresh user credentials when system restarts
    refresh = bool(uptime > session_uptime)
    token = request.headers.get('X-Forwarded-User')
    if not (token and 'user' in session.keys()) or refresh:
        logger = logging.getLogger()
        logger.warning('Refreshing user credentials in client session')
        userinfo = askfor.get('api/system/user_info',
                               headers=request.headers
                             ).json()
        userinfo['dev_instance'] = Config.get('development')
        session['user'] = userinfo
        session['time'] = time_now
    return session['user']

def setup_logging(debug):
    """
    Setup logging format and place - console for debug mode and rotating files for production
    """
    logger = logging.getLogger()
    logger.propagate = False
    if debug:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
    else:
        if not os.path.isdir('logs'):
            os.mkdir('logs')

        handler = logging.handlers.RotatingFileHandler('logs/relval.log', 'a', 8*1024*1024, 50)
        handler.setLevel(logging.INFO)

    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s UTC][%(user)s][%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt='%d-%b-%y %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG':    'white',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    handler.setFormatter(formatter)
    handler.addFilter(UsernameFilter())
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def create_app():
    log_format = '[%(asctime)s][%(levelname)s] %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)
    # Set flask logging to warning
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    # Set paramiko logging to warning
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

    app = Flask(__name__,
                static_folder='../react_frontend/build/static',
                template_folder='../react_frontend/build'
                )
    app.config.from_object('config')

    # Add API resources
    from api.ticket_api import (CreateTicketAPI,
                                DeleteTicketAPI,
                                UpdateTicketAPI,
                                GetTicketAPI,
                                GetEditableTicketAPI,
                                CreateRelValsForTicketAPI,
                                GetWorkflowsOfCreatedRelValsAPI,
                                GetRunTheMatrixOfTicketAPI,
                                GetInputInfoForJiraAPI
                                )
    from api.relval_api import (CreateRelValAPI,
                                DeleteRelValAPI,
                                UpdateRelValAPI,
                                GetRelValAPI,
                                GetEditableRelValAPI,
                                GetCMSDriverAPI,
                                GetCMSDriverTestAPI,
                                GetConfigUploadAPI,
                                GetRelValJobDictAPI,
                                GetDefaultRelValStepAPI,
                                RelValNextStatus,
                                RelValPreviousStatus,
                                UpdateRelValWorkflowsAPI,
                                CreateDQMComparisonPlotsAPI
                                )
    from api.system_api import (LockerStatusAPI,
                                UserInfoAPI,
                                SubmissionWorkerStatusAPI,
                                SubmissionQueueAPI,
                                ObjectsInfoAPI,
                                BuildInfoAPI,
                                UptimeInfoAPI
                                )
    from api.settings_api import SettingsAPI

    from api.search_api import SearchAPI, SuggestionsAPI, WildSearchAPI

    from api.jira_api import (GetJiraTicketsAPI,
                              CreateJiraTicketAPI
                              )

    api = Api(app)

    @app.before_first_request
    def _declare_keytab():
        config = Config.load('config.cfg', os.getenv('INSTANCE', 'prod'))
        cred_file = config.get('credentials_file')
        with open(cred_file) as json_file: credentials = json.load(json_file)
        user = credentials['username']
        passwd = credentials['password']
        os.system('mkdir -p logs')
        if f'{user}.keytab' in os.listdir('logs'): return

        os.system(f'printf "%b" "addent -password -p {user}@CERN.CH -k 1 -e RC4-HMAC\n{passwd}\nwkt logs/{user}.keytab" | ktutil')
        os.system(f'kinit -kt logs/{user}.keytab {user}@CERN.CH')

    @app.route('/api', defaults={'_path': ''})
    @app.route('/api/<path:_path>')
    def api_documentation(_path):
        """
        Endpoint for API documentation HTML
        """
        docs = {}
        for endpoint, view in app.view_functions.items():
            view_class = dict(view.__dict__).get('view_class')
            if view_class is None:
                continue

            class_name = view_class.__name__
            class_doc = view_class.__doc__.strip()
            #pylint: disable=protected-access
            urls = sorted([r.rule for r in app.url_map._rules_by_endpoint[endpoint]])
            #pylint: enable=protected-access
            category = [x for x in urls[0].split('/') if x][1]
            if category not in docs:
                docs[category] = {}

            docs[category][class_name] = {'doc': class_doc, 'urls': urls, 'methods': {}}
            for method_name in view_class.methods:
                method = view_class.__dict__.get(method_name.lower())
                method_dict = {'doc': method.__doc__.strip()}
                docs[category][class_name]['methods'][method_name] = method_dict
                if hasattr(method, '__role__'):
                    method_dict['role'] = getattr(method, '__role__')

        return render_template('api_documentation.html.jinja', docs=docs)

    api.add_resource(CreateTicketAPI, '/api/tickets/create')
    api.add_resource(DeleteTicketAPI, '/api/tickets/delete')
    api.add_resource(UpdateTicketAPI, '/api/tickets/update')
    api.add_resource(GetTicketAPI, '/api/tickets/get/<string:prepid>')
    api.add_resource(GetEditableTicketAPI,
                     '/api/tickets/get_editable',
                     '/api/tickets/get_editable/<string:prepid>')
    api.add_resource(CreateRelValsForTicketAPI, '/api/tickets/create_relvals')
    api.add_resource(GetInputInfoForJiraAPI, '/api/tickets/jira_info/<string:prepid>')
    api.add_resource(GetWorkflowsOfCreatedRelValsAPI,
                 '/api/tickets/relvals_workflows/<string:prepid>')
    api.add_resource(GetRunTheMatrixOfTicketAPI, '/api/tickets/run_the_matrix/<string:prepid>')

    api.add_resource(CreateRelValAPI, '/api/relvals/create')
    api.add_resource(DeleteRelValAPI, '/api/relvals/delete')
    api.add_resource(UpdateRelValAPI, '/api/relvals/update')
    api.add_resource(GetRelValAPI, '/api/relvals/get/<string:prepid>')
    api.add_resource(GetEditableRelValAPI,
                     '/api/relvals/get_editable',
                     '/api/relvals/get_editable/<string:prepid>')
    api.add_resource(GetCMSDriverAPI, '/api/relvals/get_cmsdriver/<string:prepid>')
    api.add_resource(GetCMSDriverTestAPI, '/api/relvals/get_test/<string:prepid>')
    api.add_resource(GetConfigUploadAPI, '/api/relvals/get_config_upload/<string:prepid>')
    api.add_resource(GetRelValJobDictAPI, '/api/relvals/get_dict/<string:prepid>')
    api.add_resource(GetDefaultRelValStepAPI, '/api/relvals/get_default_step')
    api.add_resource(RelValNextStatus, '/api/relvals/next_status')
    api.add_resource(RelValPreviousStatus, '/api/relvals/previous_status')
    api.add_resource(UpdateRelValWorkflowsAPI, '/api/relvals/update_workflows')
    api.add_resource(CreateDQMComparisonPlotsAPI, '/api/relvals/compare_dqm_plots')

    api.add_resource(LockerStatusAPI, '/api/system/locks')
    api.add_resource(UserInfoAPI, '/api/system/user_info')
    api.add_resource(SubmissionWorkerStatusAPI, '/api/system/workers')
    api.add_resource(SubmissionQueueAPI, '/api/system/queue')
    api.add_resource(ObjectsInfoAPI, '/api/system/objects_info')
    api.add_resource(BuildInfoAPI, '/api/system/build_info')
    api.add_resource(UptimeInfoAPI, '/api/system/uptime')
    api.add_resource(SettingsAPI,
                     '/api/settings/get',
                     '/api/settings/get/<string:name>')

    api.add_resource(SearchAPI, '/api/search')
    api.add_resource(SuggestionsAPI, '/api/suggestions')
    api.add_resource(WildSearchAPI, '/api/wild_search')

    api.add_resource(GetJiraTicketsAPI, '/api/jira/tickets')
    api.add_resource(CreateJiraTicketAPI, '/api/jira/create')

    # Register Blueprints
    from .relvals.views import relval_blueprint
    from .home_view import home_blueprint
    from .tickets.view import ticket_blueprint
    from .dqm.view import dqm_blueprint
    from .dashboard.dashboard_view import dashboard_blueprint

    app.register_blueprint(relval_blueprint)
    app.register_blueprint(home_blueprint)
    app.register_blueprint(ticket_blueprint)
    app.register_blueprint(dqm_blueprint, url_prefix='/')
    app.register_blueprint(dashboard_blueprint)

    @app.route('/', defaults={'_path': '/'})
    @app.route('/<path:_path>')
    def catch_all(_path):
        """
        Return index.html for all paths except API
        """
        try:
            return render_template('index.html')
        except TemplateNotFound:
            response = '<script>setTimeout(function() {location.reload();}, 5000);</script>'
            response += 'Webpage is starting, please wait a few minutes...'
            return response

    CORS(app,
     allow_headers=['Content-Type',
                    'Authorization',
                    'Access-Control-Allow-Credentials', 'Access-Control-Allow-Origin'],
     supports_credentials=True)
    # To avoid trailing slashes at the end of the url
    app.url_map.strict_slashes = False
    @app.before_request
    def clear_trailing():
        from flask import redirect, request
        rp = request.path
        if rp != '/' and rp.endswith('/'):
            return redirect(rp[:-1])

    config = Config.load('config.cfg', os.getenv('INSTANCE', 'prod'))
    # Init database connection
    Database.set_database_name('relval')
    Database.set_credentials(os.getenv('DATABASE_USER'), os.getenv('DATABASE_PASSWORD'))
    Database.add_search_rename('tickets', 'created_on', 'history.0.time')
    Database.add_search_rename('tickets', 'created_by', 'history.0.user')
    Database.add_search_rename('tickets', 'workflows', 'workflow_ids<float>')
    Database.add_search_rename('relvals', 'created_on', 'history.0.time')
    Database.add_search_rename('relvals', 'created_by', 'history.0.user')
    Database.add_search_rename('relvals', 'workflows', 'workflows.name')
    Database.add_search_rename('relvals', 'workflow', 'workflows.name')
    Database.add_search_rename('relvals', 'output_dataset', 'output_datasets')

    debug = config.get('development', False)
    logger = setup_logging(debug)
    logger.info('Starting... Debug: ')
    return app
