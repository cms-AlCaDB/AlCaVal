from flask import Blueprint
from .. import oidc

relval_blueprint = Blueprint('relval', __name__)


@relval_blueprint.route('/')
@oidc.check
def get_relval():
	return "Relval page!"