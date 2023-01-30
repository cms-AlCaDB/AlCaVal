import ast
import json
import re
from flask import (Blueprint, 
                    render_template, 
                    redirect, 
                    request, 
                    flash, 
                    url_for, 
                    session, 
                    make_response,
                    jsonify)

from werkzeug.datastructures import MultiDict

from core_lib.utils.connection_wrapper import ConnectionWrapper
from core_lib.utils.global_config import Config
from resources.oms_api import OMSAPI
from .forms import TicketForm
from .. import get_userinfo

from resources.smart_tricks import askfor, DictObj

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
grid_cert = Config.get('grid_user_cert')
grid_key = Config.get('grid_user_key')
cmsweb_url = 'https://cmsweb.cern.ch'

ticket_blueprint = Blueprint('tickets', __name__, url_prefix='/tickets', template_folder='templates', static_folder='static')

@ticket_blueprint.route('/edit', methods=['GET', 'PUT', 'POST'])
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
        input_runs = formdata.get('input_runs')
        input_datasets = formdata.get('input_datasets')
        # command_steps = formdata.get('command_steps')
        formdata.update({'workflow_ids': ", ".join([str(i) for i in workflows])})
        if isinstance(input_datasets, list):
            formdata.update({'input_datasets': "\n".join([str(i) for i in input_datasets])})
        if isinstance(input_runs, list):
            formdata.update({'input_runs': ", ".join([str(i) for i in input_runs])})
        # formdata.update({'command_steps': ", ".join([str(i) for i in command_steps])})

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
                form._fields.get(field).render_kw.update({'readonly': not editInfo.get(field)})
            else:
                form._fields.get(field).render_kw = {'readonly': not editInfo.get(field)}
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
                form._fields.get(key).render_kw.update({'readonly': False})

    if form.validate_on_submit():
        data = form.data
        data.update({'workflow_ids': data['workflow_ids'].strip().split(',')})
        input_datasets = data['input_datasets'].replace(',', '\n').split('\n')
        input_datasets = list(map(lambda x: x.strip(), input_datasets))
        input_datasets = list((filter(lambda x: len(x)>5, input_datasets)))
        data.update({'input_datasets': input_datasets})
        # data.update({'command_steps': data['command_steps'].strip().split(',')})
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

@ticket_blueprint.route('', strict_slashes=False, methods=['GET'])
def tickets():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=tickets' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = ItemTable(items, classes=['table', 'table-hover'])
    itemdict = DictObj({value['_id']: value for value in items})
    itemdict = {value['_id']: value for value in items}
    return render_template('Tickets.html.jinja', user_name=user['response']['fullname'], user=user, table=table, userinfo=user['response'], items = json.dumps(itemdict))

@ticket_blueprint.route('/fetch-events', methods=['POST'])
def fetch_events():
    data = json.loads(request.data.decode('utf-8'))
    response = validateDataAndFetchEvents(data)
    return jsonify(response)

def validateDataAndFetchEvents(data):
    datasets = data.get('datasets')
    runs = data.get('runs')
    resp = {'success': False}
    if not datasets:
        test_datasets = list()
    else:
        test_datasets = datasets.replace(',', '\n').split('\n')
        test_datasets = list(map(lambda x: x.strip(), test_datasets))
        test_datasets = list((filter(lambda x: len(x)>0, test_datasets)))
    wrong_datasets = list()
    if test_datasets:
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for dataset in test_datasets:
                regex = r'^/[a-zA-Z0-9\-_]{1,99}/[a-zA-Z0-9\.\-_]{1,199}/[A-Z\-]{1,50}$'
                if not re.fullmatch(regex, dataset):
                    wrong_datasets.append(dataset)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/datasets?dataset={dataset}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_datasets.append(dataset)

    if wrong_datasets:
        resp['response'] = f'Invalid datasets: {", ".join(wrong_datasets)}'
        return resp
    elif not datasets.strip():
        resp['response'] = f"Dataset names are not provided."
        return resp
    resp = validate_input_runs(runs, test_datasets)
    return resp

def validate_input_runs(runstring, datasets=[]):
    resp = {'success': False }
    try:
        if not runstring:
            test_runs = list()
        elif not ('{' in runstring and '}' in runstring):
            test_runs = list(map(lambda x: x.strip(), runstring.split(',')))
        elif isinstance(ast.literal_eval(runstring), dict):
            test_runs = list(ast.literal_eval((runstring)).keys())
        else: raise Exception
    except Exception as e:
        resp['response']='Accepted only comma separated list of runs \
                                or JSON formatted lumisections'
        return resp
    wrong_runs = list()
    if test_runs:
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for run in test_runs:
                if not re.fullmatch(r'^\d{6}$', run):
                    wrong_runs.append(run)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/runs?run_num={run}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_runs.append(run)
    if wrong_runs:
        resp['response']=f'Invalid runs: {", ".join(wrong_runs)}'
        return resp
    if (not runstring.strip()) and datasets:
        resp['response']=f"Run numbers field is required when 'Dataset' field is provided"
        return resp

    # Test if given runs are available in all datasets
    incompatible_runs = {d: [] for d in datasets}
    files_info = {d: 0 for d in datasets}
    with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
        for dataset in datasets:
            runs_in_dataset = dbs_conn.api(
                    'GET',
                    f'/dbs/prod/global/DBSReader/runs?dataset={dataset}'
                    )
            res = json.loads(runs_in_dataset.decode('utf-8'))
            res = {a_dict['run_num'] for a_dict in res}
            bad_runs = list(set([int(a) for a in test_runs]).difference(res))
            incompatible_runs[dataset] = bad_runs

            # Filling files number info
            for RunNumb in test_runs:
                run_numbers = ast.literal_eval((runstring))
                runWithLumi = isinstance(run_numbers, dict)
                if runWithLumi:
                    LumiSec = str(run_numbers[RunNumb]).replace(' ', '')
                LumiSec = f'&lumi_list={LumiSec}' if runWithLumi else ''
                files = dbs_conn.api('GET',
                f'/dbs/prod/global/DBSReader/files?dataset={dataset}&run_num={RunNumb}{LumiSec}',
                )
                files_info[dataset] += len(json.loads(files.decode('utf-8')))

    if [v for _, v in incompatible_runs.items() if v]:
        msg = "<ul style='list-style-type: none; padding: 0;'>"
        for k, v in incompatible_runs.items():
            nRuns = len(v) > 1
            if v:
                msg += f"<li>Run{'s' if nRuns else ''} \
                    {', '.join([str(l) for l in v])} \
                    {'are' if nRuns else 'is'} not \
                    present in <code>{k}</code> </li>"
        msg+='</ul>'
        resp['response'] = msg
        return resp

    # Validate if lumisections range is correctly casted
    runs = ast.literal_eval(runstring)
    if isinstance(runs, dict):
        for _, value in runs.items():
            is_list = isinstance(value, list)
            is_int = all(
                (len(items) == 2 if isinstance(items, list) else False) and\
                isinstance(items, list) and \
                all(isinstance(item, int) for item in items) for items in value
            )
            if is_list and is_int:
                lsec = []
                for v in value: lsec += v
                asc_range = True if lsec == sorted(lsec) else False
            else:
                asc_range = False
            if not (is_list and is_int and asc_range):
                resp['response'] = f'<p>Lumisections format is not valid. \
                    It should be list of list of lumisection ranges. \
                    e.g. [[1 ,40],[100, 200]]</p>'
                return resp

    # Validating number of events
    try:
        oms = OMSAPI()
        stats = {}
        for dataset in datasets:
            dname = dataset.split('/')[1].strip()
            events = 0
            for run in test_runs:
                if isinstance(runs, dict):
                    events += oms.get_nEvents(dname, run, LumiSec=str(runs[run]))
                else:
                    events += oms.get_nEvents(dname, run)
            stats[dataset] = events
        msg = "<ul>"
        for dataset, events in stats.items():
            msg += f"<li><code>{dataset}</code>: <span style='color:blue'>{'{:,}'.format(events)}</span> events and {files_info[dataset]} files</li>"
        msg += "</ul>"

    except Exception as e:
        resp['response'] = e
        return resp
    return {'response': msg, 'success': True}
    