import json
import requests
from flask import (Blueprint,
					render_template,
					redirect,
					request,
					flash,
					url_for,
					session,
					make_response
					)
from .. import oidc, get_userinfo

from resources.smart_tricks import askfor, DictObj

dashboard_blueprint = Blueprint('dashboard', __name__, url_prefix='/dashboard', template_folder='templates', static_folder='static')

@dashboard_blueprint.route('', strict_slashes=False, methods=['GET'])
@oidc.check
def show_dashboard():
	user = get_userinfo()
	return render_template('Dashboard.html.jinja')
