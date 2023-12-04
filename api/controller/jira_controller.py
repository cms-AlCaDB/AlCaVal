import json
import logging
from jira import JIRA
from core_lib.utils.global_config import Config

class JiraTicketController():
    """
    Jira ticket controller performs all actions with tickets
    """

    def __init__(self):
        self.database_name = 'tickets'
        self.jira = Jira(Config.get('jira_credentials_file'))

    def get(self):
        # Summaries of my last 50 reported issues
        connection = self.jira.setup_jira_connection()
        issues = connection.search_issues('project=CMSALCA order by created desc', maxResults=50)
        connection.close()
        return issues

    def create_ticket(self, jira_json):
        components = [a.strip() for a in jira_json['jira_components'].split(',')]
        fields={
                'project': 'CMSALCA',
                'issuetype': {'name': 'Task'},
                'summary': jira_json['jira_summary'],
                'description': jira_json['jira_description'],
                'assignee': {'name': 'matheus'},
                'priority': {'name': 'Major'},
                'components': [{'name' : 'AlCaDB'}] + [{'name': a} for a in components],
                'labels': [l.strip() for l in jira_json['jira_labels'].split(',')]
               }
        connection = self.jira.setup_jira_connection()
        new_issue = connection.create_issue(fields = fields)
        connection.close()
        return new_issue.key

    def add_comment(self, text):
        connection = self.jira.setup_jira_connection()
        issue = connection.issue('CMSALCA-{}'.format(self.args['Jira']))
        comment = connection.add_comment(issue.key, text)
        connection.close()

class Jira():
    def __init__(self, credentials_file, host='https://its.cern.ch/jira'):
        self.client = None
        self.logger = logging.getLogger()
        self.credentials_file = credentials_file
        self.host = host

    def setup_jira_connection(self):
        with open(self.credentials_file) as json_file:
            credentials = json.load(json_file)

        options = {'check_update': False}
        self.client  = JIRA(self.host, 
                            token_auth=(credentials["token"]), 
                            options=options)
        self.logger.debug('Done setting up jira connection')
        return self.client
