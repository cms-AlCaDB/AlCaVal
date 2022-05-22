from flask import Blueprint, render_template, redirect, request
from . import oidc, get_userinfo

home_blueprint = Blueprint('home', __name__)

@home_blueprint.route('/')
@oidc.check
def index():
	user = get_userinfo()
	return render_template('Home.html.jinja', user_name=user['response']['fullname'], user=user)