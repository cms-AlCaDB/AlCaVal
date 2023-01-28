import json
from copy import deepcopy, copy
from flask import (Blueprint,
                    request,
                    render_template,
                    session,
                    jsonify,
                    make_response,
                    flash,
                    redirect,
                    url_for
                  )
from werkzeug.datastructures import MultiDict
from .. import oidc, get_userinfo
from resources.smart_tricks import askfor
from .Table import RelvalTable
from .relval_forms import RelvalForm, StepsForm

relval_blueprint = Blueprint('relvals', __name__, url_prefix='/relvals', template_folder='templates', static_folder='static')


@relval_blueprint.route('', strict_slashes=False, methods=['GET'])
@oidc.check
def get_relval():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=relvals' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = RelvalTable(items, classes=['table', 'table-hover'])

    ticket = request.args.get('ticket')
    prepid = request.args.get('prepid')
    return render_template('Relvals.html.jinja', user_name=user['response']['fullname'], user=user,
                            table=table, userinfo=user['response'], 
                            ticket=ticket, prepid=prepid
                          )

def prepareStepForForm(data):
    data['step_type'] = 'input' if len(data['input']['dataset'].strip())> 0 else 'driver'
    data['driver']['datatier'] = ', '.join(data['driver']['datatier'])
    data['driver']['eventcontent'] = ', '.join(data['driver']['eventcontent'])
    data['driver']['step'] = ', '.join(data['driver']['step'])
    data['input']['run'] = ', '.join([str(run) for run in data['input']['run']])
    data['input']['lumisection'] = json.dumps(data['input']['lumisection'])
    return data

def prepareDataForForm(data):
    data['step'] = data.pop('steps')
    for step in data['step']:
        if step['driver']['mc']: step['driver']['data_mc'] = 'mc'
        if step['driver']['data']: step['driver']['data_mc'] = 'data'
        step = prepareStepForForm(step)
    return data

def prepareDataFromForm(data):
    def getList(indata):
        splitList = indata.strip().split(',')
        return [p.strip() for p in splitList if p != '']

    for step in data['step']:
        step['driver']['datatier'] = getList(step['driver']['datatier'])
        step['driver']['eventcontent'] = getList(step['driver']['eventcontent'])
        step['driver']['step'] = getList(step['driver']['step'])
        step['input']['run'] = getList(step['input']['run'])
        step['input']['lumisection'] = json.loads(step['input']['lumisection'])

        step['driver']['mc'] = False
        step['driver']['data'] = False
        if step['driver']['data_mc'] == 'mc':
            step['driver']['mc'] = True
        elif step['driver']['data_mc'] == 'data':
            step['driver']['data'] = True

    data['steps'] = data.pop('step')
    return data

def applyEditingInfo(form, edit_all = False):
    def toggle_readonly(field, readonly = False):
        rkw_value = field.render_kw
        if rkw_value:
            field.render_kw.update({'readonly': readonly})
        else:
            field.render_kw = {'readonly': readonly}
    if edit_all:
        # Make all fields either readonly or editable
        for fieldname in form._fields.keys():
            toggle_readonly(form._fields.get(fieldname))
        for stepindex, step in enumerate(form.step.entries):
            for fieldname in step._fields:
                if (fieldname == 'input' or  fieldname == 'driver'):
                    for inputfield in step._fields.get(fieldname):
                        toggle_readonly(inputfield)
                    continue
                toggle_readonly(step._fields.get(fieldname))
        return form

    editInfo = session['relval_editingInfo']
    olddata = session['relval_data_for_form']
    fieldkeys = set(form._fields.keys())
    common_keys = fieldkeys.intersection(set(editInfo.keys()))
    for fieldname in common_keys:
        toggle_readonly(form._fields.get(fieldname), 
                        readonly = not editInfo.get(fieldname)
                        )
    for stepindex, step in enumerate(form.step.entries):
        for fieldname in step._fields:
            if (fieldname == 'input' or fieldname == 'driver'):
                for inputfield in step._fields.get(fieldname):
                    toggle_readonly(inputfield, 
                                    readonly= not editInfo['step']
                                    )
                continue
            toggle_readonly(step._fields.get(fieldname),
                            readonly= not editInfo['step']
                            )
    return form

@relval_blueprint.route('/edit', methods=['GET', 'PUT', 'POST'])
@oidc.check
def create_relval():
    user = get_userinfo()
    edit = bool(request.args.get('prepid'))
    clone = bool(request.args.get('clone'))
    prepid = request.args.get('prepid') if edit else request.args.get('clone') if clone else None
    creating_new = False if edit else True

    if (clone or edit) and request.method=='GET':
        # Check if relval exists
        relval = askfor.get('/api/relvals/get/' + prepid).json()
        if not relval['success']:
            return make_response(relval['message'], 404)

        res = askfor.get('/api/relvals/get_editable/%s' % prepid).json()
        relvaldata = copy(res['response']['object'])

        formdata = prepareDataForForm(relvaldata)
        editing_info = res['response']['editing_info']
        editing_info['step'] = editing_info.pop('steps')
        session['relval_data_for_form'] = formdata
        session['relvaldata'] = copy(res['response']['object'])
        session['relval_editingInfo'] = editing_info
    elif request.method=='GET':
        session['relval_data_for_form'] = None

    form = RelvalForm(data=session['relval_data_for_form'])

    mtickets = askfor.get('api/jira/tickets').json()['response']
    tickets_list = form.jira_ticket.choices + mtickets
    form.jira_ticket.choices = tickets_list
    if edit:
        form = applyEditingInfo(form)
    if clone:
        session['relval_editingInfo']['step'] = True
        form = applyEditingInfo(form)
        form._fields.get('prepid').data = ""

    if creating_new:
        """
        Somehow sometimeselements are not redering/refreshing from local storage
        so intentionally allowing fields to edit
        """
        form  = applyEditingInfo(form, edit_all=True)
        form._fields.get('workflow_id').render_kw.update({'readonly': True})

    if form.is_submitted():
        print(form.errors)
    if form.validate_on_submit():
        outdata = form.data
        outdata = prepareDataFromForm(outdata)
        if creating_new:
            res = askfor.put('api/relvals/create', data=str(json.dumps(outdata)), headers=request.headers).json()
            if res['success']: flash(u'Success! RelVal created!', 'success')
        else:
            # Merging new data with existing data to update the relval
            data = session['relvaldata'] | outdata
            stepNumbers = min(len(data['steps']), len(session['relvaldata']['steps']))
            for index in range(stepNumbers):
                data['steps'][index] = session['relvaldata']['steps'][index] | data['steps'][index] 
            #------------------------------------------------------------------
            res = askfor.post('api/relvals/update', data=json.dumps(data), headers={'X-Forwarded-Access-Token': request.headers['X-Forwarded-Access-Token']}).json()
            if res['success']: flash(u'Success! RelVal updated!', 'success')

        if res['success']:
            return redirect(url_for('relvals.get_relval', prepid=res['response'].get('prepid')))
        else:
            flash(res['message'], 'danger')

    newform = RelvalForm()
    return render_template('RelvalsEdit.html.jinja', 
                            user_name=user['response']['fullname'],
                            user=user,
                            form=form,
                            createNew=creating_new,
                            query_string = request.query_string.decode())

@relval_blueprint.route('/get_default_step', methods=['GET'])
def get_default_step():
    response = askfor.get('api/relvals/get_default_step').json()
    form = StepsForm(data=response['response'])
    return jsonify({'response': str(form.step()), 'message': ""})

def getValidJSON(jsonstep):
    """Convert input json to valid json for reinput to the form"""
    copiedjson = copy(jsonstep)
    copiedjson['step'] = []
    label = 'step ' # Step label to recognize that it is step form
    for key, value in jsonstep.items():
        if label in key:
            index = key.split(label)[1].split('-')[0]
            newkey = key.split(label)[1].split('-')[1]
            copiedjson.pop(key)
            if len(copiedjson['step']) < int(index):
                copiedjson['step'].append({})
            if newkey=='driver':
                newkey = key.split(label)[1].split('-')[2]
                if 'driver' in copiedjson['step'][int(index)-1]:
                    copiedjson['step'][int(index)-1]['driver'].update({newkey: value})
                else:
                    copiedjson['step'][int(index)-1]['driver'] = {newkey: value}
                continue
            if newkey=='input':
                newkey = key.split(label)[1].split('-')[2]
                if 'input' in copiedjson['step'][int(index)-1]:
                    copiedjson['step'][int(index)-1]['input'].update({newkey: value})
                else:
                    copiedjson['step'][int(index)-1]['input'] = {newkey: value}
                continue
            copiedjson['step'][int(index)-1].update({newkey: value})
    return copiedjson

@relval_blueprint.route('/add_step', methods=['GET', 'PUT'])
@oidc.check
def add_step():
    """Dynamically adding new steps to the relval form"""
    user = get_userinfo()
    response = askfor.get('api/relvals/get_default_step').json()
    jsonstep = None
    if request.method == 'PUT':
        jsonstep = json.loads(request.data.decode('utf-8'))
    request.method = 'GET'
    copiedjson = getValidJSON(jsonstep)
    copiedjson['step'].append(prepareStepForForm(response['response']))

    form = StepsForm(data=copiedjson)
    print(request.args)
    edit = bool(request.args.get('prepid'))
    if not edit:
        form = applyEditingInfo(form, edit_all=True)

    return jsonify({'response': str(form.step()), 
        'message': "These are the steps in the relval form. \
        Can be use for dynamically adding new steps"})


@relval_blueprint.route('/delete_step/<int:stepid>', methods=['PUT'])
@oidc.check
def delete_step(stepid):
    """Dynamically deleting new steps from the relval form"""
    user = get_userinfo()
    if request.method == 'PUT':
        jsonstep = json.loads(request.data.decode('utf-8'))
    # Required to render form fields
    request.method = 'GET'
    copiedjson = getValidJSON(jsonstep)
    copiedjson['step'].pop(stepid-1)
    form = StepsForm(data=copiedjson)

    edit = bool(request.args.get('prepid'))
    if not edit:
        form = applyEditingInfo(form, edit_all=True)
    return jsonify({'response': str(form.step()),
        'inputdata': jsonstep,
        'message': "These are the steps in the relval form. \
        Can be use for dynamically deleting any step"})

@relval_blueprint.route('/local_test_result/<prepid>', methods=['GET'])
@oidc.check
def get_relvals_react(prepid):
    """Display local test result of a relval"""
    return render_template('LocalTest.html.jinja',
                            prepid=prepid,
                          )
