import json
import logging
from database.database import Database
from ..model.model_base import ModelBase
from ..utils.locker import Locker
from ..utils.exceptions import ObjectAlreadyExists, ObjectNotFound

class ControllerBase():
    def __init__(self):
        self.logger = logging.getLogger()
        self.locker = Locker()
        self.database_name = None
        self.model_class = ModelBase

    def create(self, json_data):
        """
        Create a new object from given json_data
        """
        json_data['history'] = []
        if '_id' in json_data:
            del json_data['_id']

        new_object = self.model_class(json_input=json_data)
        prepid = new_object.get_prepid()
        print(prepid)

        database = Database(self.database_name)
        if database.get(prepid):
            raise ObjectAlreadyExists(prepid, self.database_name)

        with self.locker.get_lock(prepid):
            self.logger.info('Will create %s', (prepid))
            new_object.add_history('create', prepid, None)
            if not self.check_for_create(new_object):
                self.logger.error('Error while checking new item %s', prepid)
                return None

            self.before_create(new_object)
            if not database.save(new_object.get_json()):
                raise Exception(f'Error saving {prepid} to database')

            self.after_create(new_object)

        return new_object

    def get_highest_serial_number(self, database, query):
        """
        Return a sequence number of "highest" _id, including deleted
        """
        results = database.query(f'_id={query}',
                                 limit=1,
                                 sort_attr='_id',
                                 sort_asc=False,
                                 include_deleted=True)
        if not results:
            serial_number = 0
        else:
            serial_number = int(results[0]['_id'].split('-')[-1])

        self.logger.debug('Highest serial number for %s is %s', query, serial_number)
        return serial_number

    def check_for_create(self, obj):
        """
        Perform checks on object before adding it to database
        """
        return True

    def before_create(self, obj):
        """
        Actions to be performed before object is updated
        """
        return

    def after_create(self, obj):
        """
        Actions to be performed after object is updated
        """
        return