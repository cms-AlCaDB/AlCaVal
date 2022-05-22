import os
import sys
import logging
import logging.handlers
from flask import Flask, request, session
from flask_restful import Api
from flask_cors import CORS
from database.database import Database
from core_lib.utils.global_config import Config
from core_lib.utils.username_filter import UsernameFilter
from flask_oidc import OpenIDConnect                                            
oidc = OpenIDConnect()

from resources.smart_tricks import askfor, DictObj
def get_userinfo():
    userinfo = askfor.get('api/system/user_info', headers=request.headers).json()
    user = DictObj(userinfo)
    session['user'] = userinfo
    return user

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

    formatter = logging.Formatter(fmt='[%(asctime)s][%(user)s][%(levelname)s] %(message)s')
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

	app = Flask(__name__)
	app.config.from_object('config')
	oidc.init_app(app)

	# Add API resources
	from api.ticket_api import (CreateTicketAPI, 
								DeleteTicketAPI,
	                            UpdateTicketAPI,
	                            GetTicketAPI,
	                            GetEditableTicketAPI,
	                            CreateRelValsForTicketAPI,
	                            GetWorkflowsOfCreatedRelValsAPI,
	                            GetRunTheMatrixOfTicketAPI)
	from api.relval_api import (CreateRelValAPI,
                            DeleteRelValAPI,
                            UpdateRelValAPI,
                            GetRelValAPI,
                            GetEditableRelValAPI,
                            GetCMSDriverAPI,
                            GetConfigUploadAPI,
                            GetRelValJobDictAPI,
                            GetDefaultRelValStepAPI,
                            RelValNextStatus,
                            RelValPreviousStatus,
                            UpdateRelValWorkflowsAPI)
	from api.system_api import UserInfoAPI
	from api.search_api import SearchAPI, SuggestionsAPI, WildSearchAPI

	from api.jira_api import GetJiraTicketsAPI

	api = Api(app)
	api.add_resource(CreateTicketAPI, '/api/tickets/create')
	api.add_resource(DeleteTicketAPI, '/api/tickets/delete')
	api.add_resource(UpdateTicketAPI, '/api/tickets/update')
	api.add_resource(GetTicketAPI, '/api/tickets/get/<string:prepid>')
	api.add_resource(GetEditableTicketAPI, 
					 '/api/tickets/get_editable', 
					 '/api/tickets/get_editable/<string:prepid>')
	api.add_resource(CreateRelValsForTicketAPI, '/api/tickets/create_relvals')
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
	api.add_resource(GetConfigUploadAPI, '/api/relvals/get_config_upload/<string:prepid>')
	api.add_resource(GetRelValJobDictAPI, '/api/relvals/get_dict/<string:prepid>')
	api.add_resource(GetDefaultRelValStepAPI, '/api/relvals/get_default_step')
	api.add_resource(RelValNextStatus, '/api/relvals/next_status')
	api.add_resource(RelValPreviousStatus, '/api/relvals/previous_status')
	api.add_resource(UpdateRelValWorkflowsAPI, '/api/relvals/update_workflows')


	api.add_resource(UserInfoAPI, '/api/system/user_info')
	api.add_resource(SearchAPI, '/api/search')
	api.add_resource(SuggestionsAPI, '/api/suggestions')
	api.add_resource(WildSearchAPI, '/api/wild_search')

	api.add_resource(GetJiraTicketsAPI, '/api/jira/tickets')

	# Register Blueprints
	from .relvals.views import relval_blueprint
	from .home_view import home_blueprint
	from .tickets.view import ticket_blueprint
	from .dqm.view import dqm_blueprint

	app.register_blueprint(relval_blueprint, url_prefix='/')
	app.register_blueprint(home_blueprint, url_prefix='/')
	app.register_blueprint(ticket_blueprint, url_prefix='/')
	app.register_blueprint(dqm_blueprint, url_prefix='/')

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

	config = Config.load('config.cfg', 'prod')
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

	logger = setup_logging(True)
	logger.info('Starting... Debug: ')
	return app
