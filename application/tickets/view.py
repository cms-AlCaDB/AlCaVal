import json
import requests
from flask import Blueprint, render_template, redirect, request, flash, url_for
from .forms import TicketForm
from .. import oidc, get_userinfo

from resources.smart_tricks import askfor

ticket_blueprint = Blueprint('tickets', __name__, template_folder='templates')

@ticket_blueprint.route('/tickets/edit', methods=['GET', 'POST'])
@oidc.check
def create_ticket():
    user = get_userinfo()
    form = TicketForm()
    if form.validate_on_submit():
        data = form.data
        res = askfor.put('api/tickets/create', data=data, headers=request.headers).json()
        if res['success']:
            flash(u'Success! Ticket created!', 'success')
        else:
            flash(res['message'], 'danger')
    return render_template('TicketEdit.html.jinja', user_name=user.response.fullname, form=form)


# Tickets table
from .Table import ItemTable

@ticket_blueprint.route('/tickets', methods=['GET'])
@oidc.check
def tickets():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=tickets' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = ItemTable(items, classes=['table', 'table-hover'])
    return render_template('Tickets.html.jinja', user_name=user.response.fullname, table=table)