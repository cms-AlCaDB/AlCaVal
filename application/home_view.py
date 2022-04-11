from flask import Blueprint, render_template, redirect, request
from . import oidc
from api.utils.user_info import UserInfo

home_blueprint = Blueprint('home', __name__)

@home_blueprint.route('/')
@oidc.check
def index():
	user_info = UserInfo()
	user_name = user_info.get_user_name()
	return render_template('base.html', user_name=user_name)