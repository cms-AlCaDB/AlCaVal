import json
import requests
from flask import Blueprint, render_template, redirect, request, flash, url_for, session, make_response
from werkzeug.datastructures import MultiDict
from .forms import TicketForm
from .. import oidc, get_userinfo

from resources.smart_tricks import askfor, DictObj

ticket_blueprint = Blueprint('tickets', __name__, template_folder='templates', static_folder='static')

@ticket_blueprint.route('/tickets/edit', methods=['GET', 'PUT', 'POST'])
@oidc.check
def create_ticket():
    user = get_userinfo()
    edit = bool(request.args.get('prepid'))
    clone = bool(request.args.get('clone'))
    prepid = request.args.get('prepid') if edit else request.args.get('clone') if clone else None
    creating_new = False if edit else True

    if (clone or edit) and request.method=='GET':
        # Check if ticket exists
        ticket = askfor.get('/api/tickets/get/' + prepid).json()
        if not ticket['success']:
            return make_response(ticket['message'], 404)

        res = askfor.get('/api/tickets/get_editable/%s' % prepid).json()
        formdata = res['response']['object']

        # workflow IDs to string
        workflows = formdata.get('workflow_ids')
        command_steps = formdata.get('command_steps')
        formdata.update({'workflow_ids': ", ".join([str(i) for i in workflows])})
        formdata.update({'command_steps': ", ".join([str(i) for i in command_steps])})

        editing_info = res['response']['editing_info']
        session['ticket_data'] = formdata
        session['ticket_editingInfo'] = editing_info

    elif request.method=='GET':
        "Create TICKET"
        session['ticket_data'] = None

    form = TicketForm(data=MultiDict(session['ticket_data']))

    mtickets = askfor.get('api/jira/tickets').json()['response']
    tickets_list = form.jira_ticket.choices + mtickets
    form.jira_ticket.choices = tickets_list
    if edit:
        editInfo = session['ticket_editingInfo']
        olddata = session['ticket_data']
        common_keys = set(form._fields.keys()).intersection(set(editInfo.keys()))
        for field in common_keys:
            rkw_value = form._fields.get(field).render_kw
            if rkw_value:
                form._fields.get(field).render_kw.update({'disabled': not editInfo.get(field)})
            else:
                form._fields.get(field).render_kw = {'disabled': not editInfo.get(field)}
    if clone:
        form._fields.get('prepid').data = ""

    if creating_new:
        """
        Somehow sometimeselements are not redering/refreshing from local storage
        so intentionally allowing fields to edit
        """
        for key in form._fields.keys():
            if key in ['prepid', 'submit', 'csrf_token']:
                continue
            else:
                form._fields.get(key).render_kw.update({'disabled': False})

    if form.validate_on_submit():
        data = form.data
        data.update({'workflow_ids': data['workflow_ids'].strip().split(',')})
        data.update({'command_steps': data['command_steps'].strip().split(',')})
        if creating_new:
            res = askfor.put('api/tickets/create', data=str(json.dumps(data)), headers=request.headers).json()
            if res['success']: flash(u'Success! Ticket created!', 'success')
        else:
            data = olddata | data
            res = askfor.post('api/tickets/update', data=str(json.dumps(data)), headers=request.headers).json()
            if res['success']: flash(u'Success! Ticket updated!', 'success')

        if res['success']:
            return redirect(url_for('tickets.tickets', prepid=res['response'].get('prepid')))
        else:
            flash(res['message'], 'danger')
    return render_template('TicketEdit.html.jinja', user_name=user['response']['fullname'], user=user, form=form, createNew=creating_new)



# Tickets table
from .Table import ItemTable

@ticket_blueprint.route('/tickets', methods=['GET'])
@oidc.check
def tickets():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=tickets' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = ItemTable(items, classes=['table', 'table-hover'])
    itemdict = DictObj({value['_id']: value for value in items})
    itemdict = {value['_id']: value for value in items}
    return render_template('Tickets.html.jinja', user_name=user['response']['fullname'], user=user, table=table, userinfo=user['response'], items = json.dumps(itemdict))