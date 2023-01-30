from flask import (Blueprint,
					render_template
					)
from .. import get_userinfo


dashboard_blueprint = Blueprint('dashboard', __name__, url_prefix='/dashboard', template_folder='templates', static_folder='static')

@dashboard_blueprint.route('', strict_slashes=False, methods=['GET'])
def show_dashboard():
	user = get_userinfo()
	return render_template('Dashboard.html.jinja')
