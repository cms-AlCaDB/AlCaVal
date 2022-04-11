import json
import flask
from flask import jsonify, request
from .api_base import APIBase
from application import oidc
from .controller.ticket_controller import TicketController

ticket_controller = TicketController()

class CreateTicketAPI(APIBase):
    def __init__(self):
        APIBase.__init__(self) 

    @APIBase.ensure_role('manager')
    def put(self):
        ticket_json = dict(request.form)
        ticket_json.update({'workflow_ids': ticket_json['workflow_ids'].strip().split(',')})
        obj = ticket_controller.create(ticket_json)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})
