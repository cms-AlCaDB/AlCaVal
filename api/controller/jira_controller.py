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
        jira = Jira(Config.get('jira_credentials_file'))
        self.conn = jira.setup_jira_connection()

    def get(self):
        # Summaries of my last 50 reported issues
        issues = self.conn.search_issues('project=CMSALCA order by created desc', maxResults=50)
        return issues

    def create_ticket(self, jira_json):
        fields={
                'project': 'CMSALCA',
                'issuetype': {'name': 'Task'},
                'summary': jira_json['jira_summary'],
                'description': jira_json['jira_description'],
                'assignee': {'name': 'tvami'},
                'priority': {'name': 'Major'},
                'components': [{'name' : 'AlCaDB'}]
               }
        new_issue = self.conn.create_issue(fields = fields)
        return new_issue.key

    def add_comment(self, text):
        issue = self.conn.issue('CMSALCA-{}'.format(self.args['Jira']))
        comment = self.conn.add_comment(issue.key, text)

class Jira():
    def __init__(self, credentials_file, host='http://its.cern.ch/jira'):
        self.client = None
        self.logger = logging.getLogger()
        self.credentials_file = credentials_file
        self.host = host

    def setup_jira_connection(self):
        with open(self.credentials_file) as json_file:
            credentials = json.load(json_file)

        options = {'check_update': False}
        self.client  = JIRA(self.host, 
                            basic_auth=(credentials['username'], 
                                        credentials['password']), 
                            options=options)
        self.logger.debug('Done setting up jira connection')
        return self.client