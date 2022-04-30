"""
Module for accessing JIRA project
"""
import flask
from core_lib.api.api_base import APIBase
from .controller.jira_ticket_controller import JiraTicketController

jira_ticket_controller = JiraTicketController()

class CreateJiraTicketAPI(APIBase):
	"""Creating new JIRA ticket"""
	def __init__(self):
		APIBase.__init__(self)

	@APIBase.ensure_request_data
	@APIBase.exceptions_to_errors
	@APIBase.ensure_role('manager')
	def put(self):
		"""
		Create a ticket with the provided JSON content
		"""
		return self.output_text({'response': {}, 'success': True, 'message': ''})

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
        obj = jira_ticket_controller.get()
        issues = []
        for issue in obj:
	        issues.append((issue.key, issue.key+': '+issue.fields.summary))
        return self.output_text({'response': issues, 'success': True, 'message': ''})