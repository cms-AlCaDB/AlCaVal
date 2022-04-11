import json
import requests
from flask import Blueprint, render_template, redirect, request
from .forms import TicketForm
from .. import oidc
from resources.smart_tricks import askfor, DictObj

ticket_blueprint = Blueprint('tickets', __name__, template_folder='templates')

@ticket_blueprint.route('/edit', methods=['GET', 'POST'])
@oidc.check
def create_ticket():
	form = TicketForm()
	if form.validate_on_submit():
		data = form.data
		res = askfor.put('api/tickets/create', data = data, headers=request.headers)
	userinfo = askfor.get('api/system/user_info', headers=request.headers).json()
	user = DictObj(userinfo)
	return render_template('index.html', user_name=user.response.fullname, form=form)