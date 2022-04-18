from flask import Blueprint, request, render_template
from .. import oidc, get_userinfo
from resources.smart_tricks import askfor
from .Table import RelvalTable

relval_blueprint = Blueprint('relvals', __name__, template_folder='templates')


@relval_blueprint.route('/relvals', methods=['GET'])
@oidc.check
def get_relval():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=relvals' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = RelvalTable(items, classes=['table', 'table-hover'])
    return render_template('Relvals.html.jinja', user_name=user.response.fullname, table=table, userinfo=user.response)