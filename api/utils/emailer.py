"""
Module that handles all email notifications
"""
from core_lib.utils.emailer import Emailer as BaseEmailer
from core_lib.utils.global_config import Config


class Emailer(BaseEmailer):
    """
    Emailer sends email notifications to users
    """

    def send(self, subject, body, recipients, attachment=None):
        body = body.strip()  + '\n\nSincerely,\nRelVal Machine for AlCaDB'
        if Config.get('development'):
            subject = f'[RelVal-DEV] {subject}'
        else:
            subject = f'[RelVal] {subject}'

        super().send(subject, body, recipients, attachment=attachment)

    def send_with_mime(self, subject, body, recipients, attachment=None):
        body = body.strip()  + '\n\nSincerely,\nRelVal Machine for AlCaDB'
        if Config.get('development'):
            subject = f'[RelVal-DEV] {subject}'
        else:
            subject = f'[RelVal] {subject}'

        super().send_with_mime(subject, body, recipients, attachment=attachment)