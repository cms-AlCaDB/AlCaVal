
"""
This module contans UsernameFilter class
"""
import logging
from flask import has_request_context, request

class UsernameFilter(logging.Filter):
    """
    This is a filter that adds Adfs-Login value to the log
    """
    def filter(self, record):
        if has_request_context() and request.headers.get('X-Forwarded-User'):
            record.user = request.headers.get('X-Forwarded-User')
        else:
            record.user = 'main_thread'

        return True