"""
Module for accessing JIRA project
"""
import json
import flask
from core_lib.api.api_base import APIBase
from .controller.jira_controller import JiraTicketController

jira_controller = JiraTicketController()

class CreateJiraTicketAPI(APIBase):
    """Endpoint for creating new jira ticket"""
    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Create a ticket with the provided JSON content
        """
        data = flask.request.data
        jira_json = json.loads(data.decode('utf-8'))
        if not jira_json.get('jira_description').strip():
            message = 'Description of the new Jira ticket can NOT be empty!'
            return self.output_text({'response': None, 'success': False, 'message': message})
        if isinstance(jira_json, dict):
            if not jira_json.get('jira_prepid'):
                raise Exception('PrepID of ticket is required in the input data')
            jira_ticket = jira_controller.create_ticket(jira_json)
        else:
            raise Exception('Expected a single dict')

        result = {'jira_ticket': jira_ticket, 'prepid': jira_json.get('jira_prepid')}
        return self.output_text({'response': result, 'success': True, 'message': ''})

class GetJiraTicketsAPI(APIBase):
    """
    Endpoint for retrieving list of recent tickets
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get a list of jira tickets
        """
        obj = jira_controller.get()
        issues = []
        for issue in obj:
            issues.append((issue.key, issue.key+': '+issue.fields.summary))
        return self.output_text({'response': issues, 'success': True, 'message': ''})
