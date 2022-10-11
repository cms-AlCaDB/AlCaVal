import json
from pprint import pprint
from copy import deepcopy, copy
from flask import (Blueprint,
                    render_template,
                    redirect,
                    request,
                    flash,
                    url_for,
                    session,
                    make_response, 
                    jsonify)
from .. import oidc, get_userinfo
from resources.smart_tricks import askfor
from .ComparisonForm import ComparisonForm, SetForm

dqm_blueprint = Blueprint('dqm', __name__, template_folder='templates', static_folder='static')

good_status = {'normal-archived', 'announced'}

@dqm_blueprint.route('/dqm')
@oidc.check
def index():
    user = get_userinfo()
    return render_template('DQMHome.html.jinja')

def get_dataset_choices(relvals):
    """Return list of dataset from relvals"""
    def get_choices(relvals):
        choices = []
        for relval in relvals:
            for dataset in relval['output_datasets']:
                if 'DQMIO' in dataset:
                    status = relval.get('workflows')[-1].get('status_history')
                    status = [k['status'] for k in status][-1]
                    choices.append([dataset, relval['prepid'], status])
        choices.sort()
        return choices
    try:
        choices = get_choices(relvals)
    except Exception as e:
        print(e)
        relvals=update_workflows(relvals)
        choices = get_choices(relvals)
    return choices

@dqm_blueprint.route('/dqm/compare', methods=['GET', 'PUT', 'POST'])
@oidc.check
def compare_dqm():
    user = get_userinfo()
    query_string = 'status=submitted|done'
    response = askfor.get('api/search?db_name=relvals' +'&'+ query_string).json()
    jira_tickets = {res['jira_ticket'] for res in response['response']['results']}
    jira_tickets.discard('None')
    jira_choices = [[jira, jira] for jira in jira_tickets]
    jira_choices.sort(reverse=True)

    form = ComparisonForm()
    form.jira_ticket.choices = form.jira_ticket.choices + jira_choices

    if form.data:
        query_string = 'jira_ticket='+form.data['jira_ticket']+'&status=submitted|done'
        response = askfor.get('api/search?db_name=relvals' +'&'+ query_string).json()
        relvals = response['response']['results']
        choices = [[v[1], v[1]] for v in get_dataset_choices(relvals) if v[2] in good_status]
        for myset in form.Set:
            myset.form.tar_relval.choices += choices
            myset.form.ref_relval.choices += choices

    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token')
        # Removing duplicate sets
        Set = form.data['Set']
        Set = [i for n, i in enumerate(Set) if i not in Set[n + 1:]]
        data['Set'] = Set
        response = askfor.post('api/relvals/compare_dqm_plots',
                                data=json.dumps(data),
                                headers=request.headers
                              ).json()
        if response['success']:
            return redirect(url_for('dqm.dqm_plots', jira_ticket=f'{data["jira_ticket"]}'))
        else:
            flash(response['message'], 'danger')
    return render_template('SubmitForComparison.html.jinja', form=form)

# Tickets table
from .DQMTable import DQMTable

@dqm_blueprint.route('/dqm/plots', methods=['GET'])
@oidc.check
def dqm_plots():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=relvals&status=submitted|done'+'&'+ request.query_string.decode()).json()
    mdata = response['response']['results']
    data = copy(mdata)
    for item in mdata:
        if not item.get('dqm_comparison'):
            data.pop(data.index(item))
        elif len(item.get('dqm_comparison'))==0:
            data.pop(data.index(item))

    items = []
    for obj in data:
        for dqms in obj['dqm_comparison']:
            item = {'source': dqms['source'],
                    'compared_with': dqms['compared_with'],
                    'dataset': dqms['target'],
                    'reference': dqms.get('reference'),
                    'overlay_plots': 'None',
                    'dqmlink': 'None',
                    'run_number': dqms.get('run_number'),
                    'jira_ticket': obj['jira_ticket'],
                    'relval': obj['prepid'],
                    'status': dqms['status']
                    }
            items.append(item)

    table = DQMTable(items, classes=['table', 'table-hover'])
    return render_template('DQMPlots.html.jinja', table=table)

def update_workflows(relvals):
    relval_list = []
    for relval in relvals:
        data = {'prepid': relval['prepid']}
        status = askfor.post('/api/relvals/update_workflows',
                            data=json.dumps(data),
                            headers=request.headers
                            ).json()
        relval_list.append(status)
    return relval_list

def getValidJSON(jsonset):
    """Convert input json to valid json for reinput to the form"""
    copiedjson = copy(jsonset)
    copiedjson['Set'] = []
    label = 'Set ' # Step label to recognize that it is step form
    for key, value in jsonset.items():
        if label in key:
            index = key.split(label)[1].split('-')[0]
            newkey = key.split(label)[1].split('-')[1]
            copiedjson.pop(key)
            if len(copiedjson['Set']) < int(index):
                copiedjson['Set'].append({})
            copiedjson['Set'][int(index)-1].update({newkey: value})
    return copiedjson

@dqm_blueprint.route('/dqm/get_submitted_dataset/<jira>')
@oidc.check
def get_submitted_dataset(jira):
    response = askfor.get('api/search?db_name=relvals&status=submitted|done' +'&jira_ticket='+jira).json()
    relvals = response['response']['results']
    choices = get_dataset_choices(relvals)
    return jsonify({'datasets': choices})

@dqm_blueprint.route('/dqm/update_workflows/<jira>')
@oidc.check
def update_workflows_for_jira(jira):
    response = askfor.get('api/search?db_name=relvals&status=submitted|done' +'&jira_ticket='+jira).json()
    relvals = response['response']['results']
    status = update_workflows(relvals)
    return jsonify(status[0])

@dqm_blueprint.route('/dqm/add_set', methods=['GET', 'PUT'])
@oidc.check
def add_set():
    """Dynamically adding new dataset pair to the dqm comparison form"""
    user = get_userinfo()
    jsonset = None
    if request.method == 'PUT':
        jsonset = json.loads(request.data.decode('utf-8'))
    request.method = 'GET'
    copiedjson = getValidJSON(jsonset)
    copiedjson['Set'].append({})

    form = SetForm(data=copiedjson)
    query_string = 'jira_ticket='+copiedjson['jira_ticket']+'&status=submitted|done'
    response = askfor.get('api/search?db_name=relvals' +'&'+ query_string).json()
    relvals = response['response']['results']
    choices = [[v[1], v[1]] for v in get_dataset_choices(relvals) if v[2] in good_status]
    for myset in form.Set:
        myset.form.tar_relval.choices += choices
        myset.form.ref_relval.choices += choices

    return jsonify({'response': str(form.Set()), 
        'message': "These are the sets in the dqm form. \
        Can be use for dynamically adding new pair of dataset"})

@dqm_blueprint.route('/dqm/add_defualt_pairs/<jira_ticket>', methods=['GET'])
@oidc.check
def add_defualt_pairs(jira_ticket):
    """Endpoint for getting list of default pairs in html form"""

    query_string = 'jira_ticket='+jira_ticket+'&status=submitted|done'
    response = askfor.get('api/search?db_name=relvals' +'&'+ query_string).json()
    relvals = response['response']['results']
    choices = [[v[1], v[1]] for v in get_dataset_choices(relvals) if v[2] in good_status]

    prepids = set([p[1] for p in choices])
    dsets = set([d.split('-')[2].strip() for d in prepids])
    default_pairs = list()
    for dname in dsets:
        for cond in ['HLT', 'Prompt', 'Express']:
            newid = [p for p in prepids if cond+'New-'+dname in p]
            refid = [p for p in prepids if cond+'Ref-'+dname in p]
            newid.sort(); refid.sort()
            if not (len(newid) and len(refid)): continue
            pair = {'tar_relval': [v[1] for v in choices if v[1]==newid[0]][0],
                    'ref_relval': [v[1] for v in choices if v[1]==refid[0]][0]}
            default_pairs.append(pair)
    inputjson = dict()
    inputjson['Set'] = default_pairs
    form = SetForm(Set=inputjson['Set'])
    for myset in form.Set:
        myset.form.tar_relval.choices += choices
        myset.form.ref_relval.choices += choices

    return jsonify({
        'response': str(form.Set()),
        'pairs': inputjson['Set']
        })

@dqm_blueprint.route('/dqm/delete_set/<int:setid>', methods=['PUT'])
@oidc.check
def delete_set(setid):
    """Dynamically deleting Set from the dqm form"""
    user = get_userinfo()
    if request.method == 'PUT':
        jsonset = json.loads(request.data.decode('utf-8'))
    # Required to render form fields
    request.method = 'GET'
    copiedjson = getValidJSON(jsonset)
    copiedjson['Set'].pop(setid-1)
    form = SetForm(data=copiedjson)
    query_string = 'jira_ticket='+copiedjson['jira_ticket']+'&status=submitted|done'
    response = askfor.get('api/search?db_name=relvals' +'&'+ query_string).json()
    relvals = response['response']['results']
    choices = [[v[1], v[1]] for v in get_dataset_choices(relvals) if v[2] in good_status]
    for myset in form.Set:
        myset.form.tar_relval.choices += choices
        myset.form.ref_relval.choices += choices

    return jsonify({'response': str(form.Set()),
        'inputdata': jsonset,
        'message': "These are the set in the DQM form. \
        Can be use for dynamically deleting any pair of dataset"})
