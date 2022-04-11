from flask import Flask
from flask_restful import Api
from database.database import Database
from flask_oidc import OpenIDConnect                                            
oidc = OpenIDConnect()

def create_app():
	app = Flask(__name__)
	app.config.from_object('config')
	
	oidc.init_app(app)

	from api.ticket_api import CreateTicketAPI
	from api.system_api import UserInfoAPI

	api = Api(app)
	api.add_resource(CreateTicketAPI, '/api/tickets/create')
	api.add_resource(UserInfoAPI, '/api/system/user_info')

	from .relval.views import relval_blueprint
	from .home_view import home_blueprint
	from .tickets.view import ticket_blueprint

	app.register_blueprint(relval_blueprint, url_prefix='/relval')
	app.register_blueprint(home_blueprint, url_prefix='/')
	app.register_blueprint(ticket_blueprint, url_prefix='/tickets')

	Database.set_database_name('relval')

	Database.add_search_rename('tickets', 'created_on', 'history.0.time')
	Database.add_search_rename('tickets', 'created_by', 'history.0.user')
	Database.add_search_rename('tickets', 'workflows', 'workflow_ids<float>')
	Database.add_search_rename('relvals', 'created_on', 'history.0.time')
	Database.add_search_rename('relvals', 'created_by', 'history.0.user')
	Database.add_search_rename('relvals', 'workflows', 'workflows.name')
	Database.add_search_rename('relvals', 'workflow', 'workflows.name')
	Database.add_search_rename('relvals', 'output_dataset', 'output_datasets')
	return app