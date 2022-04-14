"""
Module that holds various custom exceptions
"""

class ObjectNotFound(Exception):
    """
    Exception to be raised when object could not be found
    """
    def __init__(self, prepid):
        self.message = f'Object "{prepid}" could not be found'
        super().__init__(self.message)

    def __str__(self):
        return self.message


class ObjectAlreadyExists(Exception):
    """
    Exception to be raised when such object already exists (conflict)
    """
    def __init__(self, prepid, database):
        self.message = f'Object "{prepid}" already exists in database "{database}"'
        super().__init__(self.message)

    def __str__(self):
        return self.message
