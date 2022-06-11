"""
Module that contains all settings APIs
"""
from core_lib.api.api_base import APIBase
from core_lib.utils.settings import Settings


class SettingsAPI(APIBase):
    """
    Endpoint for getting a value from settings
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def get(self, name=None):
        """
        Get a value from settings with given name
        """
        if name:
            setting = Settings().get(name)
        else:
            setting = Settings().get_all()

        return self.output_text({'response': setting, 'success': True, 'message': ''})