"""
Module that contains all relval APIs
"""
import json
import flask
from core_lib.api.api_base import APIBase
from core_lib.utils.common_utils import clean_split
from .model.relval import RelVal
from .controller.relval_controller import RelValController


relval_controller = RelValController()


class CreateRelValAPI(APIBase):
    """
    Endpoint for creating relval
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def put(self):
        """
        Create a relval with the provided JSON content
        """
        # data = flask.request.data
        data = list(flask.request.form.keys())[0]
        relval_json = json.loads(data)
        obj = relval_controller.create(relval_json)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class DeleteRelValAPI(APIBase):
    """
    Endpoint for deleting one or multiple relvals
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def delete(self):
        """
        Delete a with the provided JSON content
        """
        data = list(flask.request.form.keys())[0]
        relval_json = data.split(',')
        if isinstance(relval_json, dict):
            results = relval_controller.delete(relval_json)
        elif isinstance(relval_json, list):
            results = []
            for prepid in relval_json:
                single_relval_json = {'prepid': prepid}
                results.append(relval_controller.delete(single_relval_json))
        else:
            raise Exception('Expected a single RelVal dict or a list of RelVal dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})


class UpdateRelValAPI(APIBase):
    """
    Endpoint for updating relvals
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Update a with the provided JSON content
        """
        data = flask.request.data
        # relval_json = json.loads(data.decode('utf-8'))
        # data = list(flask.request.form.keys())[0]
        relval_json = json.loads(data)
        if isinstance(relval_json, dict):
            results = relval_controller.update(relval_json)
        elif isinstance(relval_json, list):
            results = []
            for single_relval_json in relval_json:
                results.append(relval_controller.update(single_relval_json))
        else:
            raise Exception('Expected a single RelVal dict or a list of RelVal dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})


class GetRelValAPI(APIBase):
    """
    Endpoint for retrieving a single relval
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get a single with given prepid
        """
        obj = relval_controller.get(prepid)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})

class GetEditableRelValAPI(APIBase):
    """
    Endpoint for getting information on which relval fields are editable
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Endpoint for getting information on which relval fields are editable
        """
        if prepid:
            prepid = clean_split(prepid, ',')
            if len(prepid) == 1:
                # Return one object if there is only one prepid
                relval = relval_controller.get(prepid[0])
                editing_info = relval_controller.get_editing_info(relval)
                relval = relval.get_json()
            else:
                # Return a list if there are multiple prepids
                relval = [relval_controller.get(p) for p in prepid]
                editing_info = [relval_controller.get_editing_info(r) for r in relval]
                relval = [r.get_json() for r in relval]

        else:
            relval = RelVal()
            editing_info = relval_controller.get_editing_info(relval)
            relval = relval.get_json()

        return self.output_text({'response': {'object': relval,
                                              'editing_info': editing_info},
                                 'success': True,
                                 'message': ''})


class GetCMSDriverAPI(APIBase):
    """
    Endpoint for getting a bash script with cmsDriver.py commands of RelVal
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with RelVal's cmsDriver.py commands
        """
        relval = relval_controller.get(prepid)
        commands = relval_controller.get_cmsdriver(relval)
        return self.output_text(commands, content_type='text/plain')

class GetCMSDriverTestAPI(APIBase):
    """
    Endpoint for getting a bash script for TESTING cmsDriver.py commands 
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get cmsDriver.py command for testing
        """
        relval = relval_controller.get(prepid)
        commands = relval_controller.get_cmsdriver_test(relval)
        return self.output_text(commands, content_type='text/plain')

class GetConfigUploadAPI(APIBase):
    """
    Endpoint for getting a bash script to upload configs to ReqMgr config cache
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with relval's cmsDriver.py commands
        """
        relval = relval_controller.get(prepid)
        commands = relval_controller.get_config_upload_file(relval)
        return self.output_text(commands, content_type='text/plain')


class GetRelValJobDictAPI(APIBase):
    """
    Endpoint for getting a dictionary with job information for ReqMgr2
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with ReqMgr2's dictionary
        """
        relval = relval_controller.get(prepid)
        dict_string = json.dumps(relval_controller.get_job_dict(relval),
                                 indent=2,
                                 sort_keys=True)
        return self.output_text(dict_string, content_type='text/plain')


class GetDefaultRelValStepAPI(APIBase):
    """
    Endpoint for getting a default (empty) step that could be used as a template
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get a default sequence that could be used as a template
        """
        sequence = relval_controller.get_default_step()
        return self.output_text({'response': sequence,
                                 'success': True,
                                 'message': ''})

class RelValNextStatus(APIBase):
    """
    Endpoint for moving one or multiple RelVals to next status
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self, prepid=None):
        """
        Move one or multiple RelVals to next status
        """
        data = list(flask.request.form.keys())[0]
        relval_json = data.split(',')
        if isinstance(relval_json, dict):
            prepid = relval_json.get('prepid')
            relval = relval_controller.get(prepid)
            results = relval_controller.next_status([relval])
            results = results[0].get_json()
        elif isinstance(relval_json, list):
            relvals = []
            for single_prepid in relval_json:
                single_relval_json = {'prepid': single_prepid}
                prepid = single_relval_json.get('prepid')
                relval = relval_controller.get(prepid)
                relvals.append(relval)

            results = relval_controller.next_status(relvals)
            results = [x.get_json() for x in results]
        else:
            raise Exception('Expected a single RelVal dict or a list of RelVal dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})


class RelValPreviousStatus(APIBase):
    """
    Endpoint for moving one or multiple RelVals to previous status
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self, prepid=None):
        """
        Move one or multiple RelVals to previous status
        """
        data = flask.request.data
        relval_json = json.loads(data.decode('utf-8'))
        if isinstance(relval_json, dict):
            prepid = relval_json.get('prepid')
            relval = relval_controller.get(prepid)
            results = relval_controller.previous_status(relval)
            results = results.get_json()
        elif isinstance(relval_json, list):
            results = []
            for single_prepid in relval_json:
                single_relval_json = {'prepid': single_prepid}
                prepid = single_relval_json.get('prepid')
                relval = relval_controller.get(prepid)
                results.append(relval_controller.previous_status(relval))

            results = [x.get_json() for x in results]
        else:
            raise Exception('Expected a single RelVals dict or a list of RelVals dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})


class UpdateRelValWorkflowsAPI(APIBase):
    """
    Endpoint for trigerring one or multiple RelVal update from ReqMgr2
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Pull workflows from ReqMgr2 and update RelVal with that information
        """
        data = flask.request.data
        relval_json = json.loads(data.decode('utf-8'))
        if isinstance(relval_json, dict):
            prepid = relval_json.get('prepid')
            relval = relval_controller.get(prepid)
            results = relval_controller.update_workflows(relval)
            results = results.get_json()
        elif isinstance(relval_json, list):
            results = []
            for prepid in relval_json:
                relval = relval_controller.get(prepid)
                results.append(relval_controller.update_workflows(relval))

            results = [x.get_json() for x in results]
        else:
            raise Exception('Expected a single RelVal dict or a list of RelVal dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})

class CreateDQMComparisonPlotsAPI(APIBase):
    """
    Endpoint for comparing dqm comparison plots.
    This does not require to pass relval json.
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Create DQM comparison plots
        """
        data = list(flask.request.form.keys())[0]
        dqm_json = json.loads(data)
        if isinstance(dqm_json['Set'], list):
            results = []
            for dqm_pair in dqm_json['Set']:
                relvalT = relval_controller.get(dqm_pair.get('tar_relval'))
                relvalR = relval_controller.get(dqm_pair.get('ref_relval'))
                result = relval_controller.compare_dqm_datasets(relvalT, relvalR)
                results.append(result)
        else:
            raise Exception('Expected a single list of pair of dataset dicts')                
        return self.output_text({'response': results, 'success': True, 'message': ''})
