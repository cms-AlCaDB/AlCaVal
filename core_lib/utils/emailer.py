"""
Module that handles all email notifications
"""
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import logging
import smtplib

from core_lib.utils.global_config import Config

class Emailer():
    """
    Emailer sends email notifications to users
    """

    def __init__(self):
        self.logger = logging.getLogger()
        self.message = MIMEMultipart()

    def get_recipients(self, obj):
        """
        Return list of emails of people that are in object's history
        """
        recipients = set()
        for entry in obj.get('history'):
            user = entry['user']
            if not user or user == 'automatic':
                continue

            recipients.add(f'{user}@cern.ch')

        self.logger.info('Recipients of %s are %s',
                         obj.get_prepid(),
                         ', '.join(recipients))

        return list(recipients)

    def send_with_mime(self, subject, body, recipients, attachment=None):
        """
        Send email with MIMEMultipart
        """
        # Create a text/html message
        self.message["Subject"] = f"{subject}"
        self.message.attach(MIMEText(body.replace('\n', '<br/>'), 'html'))
        if attachment:
            with open(attachment, 'r') as fb:
                content = MIMEText(str(fb.read()))
                content.add_header('Content-Disposition',
                                    'attachment',
                                    filename='attachment.txt') 
                self.message.attach(content)
            os.remove(attachment)
        self.message['From'] = 'AlCa Service Account <alcauser@cern.ch>'
        self.message['To'] = ','.join(recipients)
        self.message['Cc'] = 'alcauser@cern.ch'

        # Send the self.message via our own SMTP server.
        smtp = smtplib.SMTP('smtp.cern.ch', 587)
        smtp.starttls()
        credentials = json.loads(open(Config.get('credentials_file')).read())
        smtp.login(*list(credentials.values()))
        self.logger.debug('Sending email %s to %s', self.message['Subject'], self.message['To'])
        try:
            smtp.send_message(self.message)
        except Exception as e:
            raise e
        smtp.quit()

    def send(self, subject, body, recipients, attachment=None):
        """Send email with text/plain format"""
        # Create a text/plain message
        message = EmailMessage()
        message.set_content(body)
        if attachment:
            with open(attachment, 'rb') as fb:
                message.add_attachment(fb.read(),
                            maintype='application',
                            subtype='text',
                            filename='attachment.txt')
            os.remove(attachment)
        message['Subject'] = subject
        message['From'] = 'AlCa Service Account <alcauser@cern.ch>'
        message['To'] = ', '.join(recipients)
        message['Cc'] = 'alcauser@cern.ch'

        # Send the message via our own SMTP server.
        smtp = smtplib.SMTP('smtp.cern.ch', 587)
        smtp.starttls()
        credentials = json.loads(open(Config.get('credentials_file')).read())
        smtp.login(*list(credentials.values()))
        self.logger.debug('Sending email %s to %s', message['Subject'], message['To'])
        smtp.send_message(message)
        smtp.quit()
