"""
Module that contains Settings class
"""
from database.database import Database


class Settings:
    """
    Class that acts as a settings getter
    """
    def __init__(self):
        self.database = Database('settings')

    def get_all(self):
        """
        Return all settings documents in the database
        """
        return self.database.query(limit=self.database.get_count())

    def get(self, setting_name, default=None):
        """
        Return value of specific setting
        """
        setting = self.database.get(setting_name)
        if setting is None:
            return default

        return setting.get('value', default)

    def save(self, setting_name, setting_value):
        """
        Save setting value to database
        """
        if not setting_name:
            return False

        return self.database.save({'_id': setting_name,
                                   'value': setting_value})