"""
Module that contains all ticket APIs
"""
import json
import flask
from core_lib.api.api_base import APIBase
from .model.ticket import Ticket
from .controller.ticket_controller import TicketController


ticket_controller = TicketController()


class CreateTicketAPI(APIBase):
    """
    Endpoint for creating a ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def put(self):
        """
        Create a ticket with the provided JSON content
        """
        ticket_json = dict(flask.request.form)
        ticket_json.update({'workflow_ids': ticket_json['workflow_ids'].strip().split(',')})
        obj = ticket_controller.create(ticket_json)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class DeleteTicketAPI(APIBase):
    """
    Endpoint for deleting tickets
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def delete(self):
        """
        Delete a ticket with the provided JSON content
        """
        data = flask.request.data
        ticket_json = json.loads(data.decode('utf-8'))
        obj = ticket_controller.delete(ticket_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class UpdateTicketAPI(APIBase):
    """
    Endpoint for updating tickets
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Update a ticket with the provided JSON content
        """
        data = flask.request.data
        ticket_json = json.loads(data.decode('utf-8'))
        obj = ticket_controller.update(ticket_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class GetTicketAPI(APIBase):
    """
    Endpoint for retrieving a single ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get a single ticket with given prepid
        """
        obj = ticket_controller.get(prepid)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class GetEditableTicketAPI(APIBase):
    """
    Endpoint for getting information on which ticket fields are editable
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Endpoint for getting information on which ticket fields are editable
        """
        if prepid:
            ticket = ticket_controller.get(prepid)
        else:
            ticket = Ticket()

        editing_info = ticket_controller.get_editing_info(ticket)
        return self.output_text({'response': {'object': ticket.get_json(),
                                              'editing_info': editing_info},
                                 'success': True,
                                 'message': ''})


class CreateRelValsForTicketAPI(APIBase):
    """
    Endpoing for creating RelVals from a ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Create RelVals for given ticket
        """
        data = flask.request.data
        request_data = json.loads(data.decode('utf-8'))
        prepid = request_data.get('prepid')
        if not prepid:
            self.logger.error('No prepid in given data: %s', json.dumps(request_data, indent=2))
            raise Exception('No prepid in submitted data')

        ticket = ticket_controller.get(prepid)
        if not ticket:
            raise Exception(f'Ticket "{prepid}" does not exist')

        result = ticket_controller.create_relvals_for_ticket(ticket)
        return self.output_text({'response': result, 'success': True, 'message': ''})


class GetWorkflowsOfCreatedRelValsAPI(APIBase):
    """
    Endpoing for getting a list of computing workflows of created RelVals
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get twiki snippet for ticket
        """
        ticket = ticket_controller.get(prepid)
        workflows = ticket_controller.get_workflows_list(ticket)
        workflows = '\n'.join(workflows)
        return self.output_text(workflows, content_type='text/plain')


class GetRunTheMatrixOfTicketAPI(APIBase):
    """
    Endpoing for getting an automatically generated runTheMatrix.py command for a gicen ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get runTheMatrix.py command of a ticket
        """
        ticket = ticket_controller.get(prepid)
        command = ticket_controller.get_run_the_matrix(ticket)
        return self.output_text(command, content_type='text/plain')
