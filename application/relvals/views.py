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

relval_blueprint = Blueprint('relvals', __name__, template_folder='templates')


@relval_blueprint.route('/relvals', methods=['GET'])
@oidc.check
def get_relval():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=relvals' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = RelvalTable(items, classes=['table', 'table-hover'])

    ticket = request.args.get('ticket')
    prepid = request.args.get('prepid')
    return render_template('Relvals.html.jinja', user_name=user['response']['fullname'], 
                            table=table, userinfo=user['response'], 
                            ticket=ticket, prepid=prepid
                          )

def prepareStepForForm(data):
    data['step_type'] = 'input' if len(data['input']['dataset'].strip())> 0 else 'driver'
    data['driver']['datatier'] = ', '.join(data['driver']['datatier'])
    data['driver']['eventcontent'] = ', '.join(data['driver']['eventcontent'])
    data['driver']['step'] = ', '.join(data['driver']['step'])
    data['input']['run'] = ', '.join(data['input']['run'])
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

def applyEditingInfo(form):
    editInfo = session['relval_editingInfo']
    olddata = session['relval_data_for_form']
    fieldkeys = set(form._fields.keys())
    # fieldkeys.remove('step')
    common_keys = fieldkeys.intersection(set(editInfo.keys()))
    def disable_fields(form, fieldname):
        field = form._fields.get(fieldname)
        rkw_value = field.render_kw
        if rkw_value:
            field.render_kw.update({'readonly': not editInfo.get(fieldname)})
        else:
            field.render_kw = {'readonly': not editInfo.get(fieldname)}
    for field in common_keys:
        disable_fields(form, field)
    # if not editInfo['step']:
    #     for stepindex, step in enumerate(form.step.entries):
    #         for fieldname in step._fields:
    #             if fieldname == 'input' and stepindex == 0:
    #                 for inputfield in step._fields.get(fieldname):
    #                     if inputfield.render_kw:
    #                         inputfield.render_kw.update({'readonly': not editInfo.get(fieldname)})
    #                     else:
    #                         inputfield.render_kw = {'readonly': not editInfo.get(fieldname)}
    #                 continue
    #             if fieldname == 'driver':
    #                 for driverfield in step._fields.get(fieldname):
    #                     if driverfield.render_kw:
    #                         driverfield.render_kw.update({'readonly': "true"})
    #                     else:
    #                         driverfield.render_kw = {'readonly': "true"}
    #                 continue
    #             if not fieldname == 'delete_step':
    #                 disable_fields(step, fieldname)
    return form

@relval_blueprint.route('/relvals/edit', methods=['GET', 'PUT', 'POST'])
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
        form._fields.get('prepid').data = ""

    if creating_new:
        """
        Somehow sometimeselements are not redering/refreshing from local storage
        so intentionally allowing fields to edit
        """
        for key in form._fields.keys():
            if key in ['prepid', 'submit', 'csrf_token', 'workflow_id']:
                continue
            else:
                form._fields.get(key).render_kw.update({'readonly': False})

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
            res = askfor.post('api/relvals/update', data=json.dumps(data), headers=request.headers).json()
            if res['success']: flash(u'Success! RelVal updated!', 'success')

        if res['success']:
            return redirect(url_for('relvals.get_relval', prepid=res['response'].get('prepid')))
        else:
            flash(res['message'], 'danger')

    newform = RelvalForm()
    return render_template('RelvalsEdit.html.jinja', 
                            user_name=user['response']['fullname'], 
                            form=form,
                            createNew=creating_new)

@relval_blueprint.route('/relvals/get_default_step', methods=['GET'])
def get_default_step():
    response = askfor.get('api/relvals/get_default_step').json()
    form = StepsForm(data=response['response'])
    return jsonify({'response': str(form.step()), 'message': ""})

def getValidJSON(jsonstep):
    # Convert input json to valid json for reinput
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

@relval_blueprint.route('/relvals/add_step', methods=['GET', 'PUT'])
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
    return jsonify({'response': str(form.step()), 
        'message': "These are the steps in the relval form. \
        Can be use for dynamically adding new steps"})


@relval_blueprint.route('/relvals/delete_step/<int:stepid>', methods=['PUT'])
@oidc.check
def delete_step(stepid):
    """Dynamically deleting new steps from the relval form"""
    user = get_userinfo()
    if request.method == 'PUT':
        jsonstep = json.loads(request.data.decode('utf-8'))
    request.method = 'GET'
    copiedjson = getValidJSON(jsonstep)
    copiedjson['step'].pop(stepid-1)
    form = StepsForm(data=copiedjson)

    return jsonify({'response': str(form.step()),
        'inputdata': jsonstep,
        'message': "These are the steps in the relval form. \
        Can be use for dynamically deleting any step"})
