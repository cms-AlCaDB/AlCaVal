from flask import Flask
from flask_restful import Api
from flask_oidc import OpenIDConnect                                            
oidc = OpenIDConnect()

def create_app():
	app = Flask(__name__)
	app.config.from_object('config')
	
	oidc.init_app(app)

	from api.ticket_api import CreateTicketAPI

	api = Api(app)
	api.add_resource(CreateTicketAPI, '/create_ticket')

	from .relval.views import relval_blueprint
	app.register_blueprint(relval_blueprint, url_prefix='/relval')

	from database.database import Database                                                                                          
	@app.route("/")
	@oidc.check
	def hello():
		Database.set_database_name('relval')                                            
		database = Database('relvals')  
		print(database.client.list_collection_names())
		return "Hello, World!"

	return app
