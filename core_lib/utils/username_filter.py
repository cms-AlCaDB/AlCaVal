
"""
This module contans UsernameFilter class
"""
import logging
from flask import has_request_context, request, g

class UsernameFilter(logging.Filter):
    """
    This is a filter that adds Adfs-Login value to the log
    """
    def filter(self, record):
        if has_request_context() and g.oidc_id_token:
            record.user = g.oidc_id_token['sub']
        else:
            record.user = 'main_thread'

        return True