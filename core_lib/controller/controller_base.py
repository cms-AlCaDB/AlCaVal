"""
Module that contains ControllerBase class
"""
import json
import logging
from database.database import Database
from core_lib.model.model_base import ModelBase
from core_lib.utils.locker import Locker
from core_lib.utils.exceptions import ObjectNotFound, ObjectAlreadyExists


class ControllerBase():
    """
    Controller base class implements simple create, read, update, delete methods
    as well as some convenience methods such as get_changed_values for update
    It also has callback methods that are called before create, update or delete actions
    This is a base class for all controllers
    It requires database name and class object of model
    """

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

    def get(self, prepid, deleted=False):
        """
        Return a single object if it exists in database
        If deleted is True, return a deleted object
        """
        database = Database(self.database_name)
        object_json = database.get(prepid)
        self.logger.debug('Fetched object for prepid %s',
                          prepid)
        if not object_json:
            raise ObjectNotFound(prepid)

        if not deleted and object_json.get('deleted'):
            # Object existed, but was deleted
            raise ObjectNotFound(prepid)

        return self.model_class(json_input=object_json, check_attributes=False)

    def update(self, new_object, force_update=False):
        """
        Update a single object with given json
        """
        # Allow either objects or their dictionaries
        if isinstance(new_object, dict):
            new_object = self.model_class(json_input=new_object)

        prepid = new_object.get_prepid()
        with self.locker.get_nonblocking_lock(prepid):
            self.logger.info('Will edit %s', prepid)
            database = Database(self.database_name)
            old_object_json = database.get(prepid)
            if not old_object_json:
                raise ObjectNotFound(prepid)

            old_object = self.model_class(json_input=old_object_json, check_attributes=False)
            # Move over history, so it could not be overwritten
            new_object.set('history', old_object.get('history'))
            changed_values = self.get_changes(old_object_json, new_object.get_json())
            if not changed_values:
                # Nothing was updated
                self.logger.info('Nothing was updated for %s', prepid)
                return old_object.get_json()

            if not force_update:
                if not self.edit_allowed(old_object, new_object, changed_values):
                    self.logger.error('Editing was not allowed for %s', prepid)

                new_object.add_history('update', changed_values, None)
                if not self.check_for_update(old_object, new_object, changed_values):
                    self.logger.error('Error while updating %s', prepid)
                    return None

            self.before_update(old_object, new_object, changed_values)
            if not database.save(new_object.get_json()):
                raise Exception(f'Error saving {prepid} to database')

            self.after_update(old_object, new_object, changed_values)
            return new_object.get_json()

    def delete(self, json_data):
        """
        Delete a single object
        """
        prepid = json_data.get('prepid', None)
        database = Database(self.database_name)
        json_data = database.get(prepid)
        if not json_data:
            raise ObjectNotFound(prepid)

        obj = self.model_class(json_input=json_data, check_attributes=False)
        with self.locker.get_nonblocking_lock(prepid, f'Deleting {prepid}'):
            self.logger.info('Will delete %s', (prepid))
            if not self.check_for_delete(obj):
                raise Exception(f'Deleting {prepid} is not allowed')

            self.before_delete(obj)
            if not database.delete_document(obj.get_json()):
                raise Exception(f'Error deleting {prepid} from database')

            self.after_delete(obj)

        return {'prepid': prepid}

    #pylint: disable=no-self-use,unused-argument
    def check_for_create(self, obj):
        """
        Perform checks on object before adding it to database
        """
        return True

    def check_for_update(self, old_obj, new_obj, changed_values):
        """
        Compare existing and updated objects to see if update is valid
        """
        return True

    def check_for_delete(self, obj):
        """
        Perform checks on object before deleting it from database
        """
        return True

    def before_create(self, obj):
        """
        Actions to be performed before object is created
        """
        return

    def after_create(self, obj):
        """
        Actions to be performed after object is created
        """
        return

    def before_update(self, old_obj, new_obj, changed_values):
        """
        Actions to be performed before object is updated
        """
        return

    def after_update(self, old_obj, new_obj, changed_values):
        """
        Actions to be performed after object is updated
        """
        return

    def before_delete(self, obj):
        """
        Actions to be performed before object is deleted
        """
        return

    def after_delete(self, obj):
        """
        Actions to be performed after object is deleted
        """
        return
    #pylint: enable=no-self-use,unused-argument

    def get_editing_info(self, obj):
        """
        Return a dictionary of pairs where key is attribute name and value is
        a boolean whether that attribute can be edited, for example
        {
          "prepid": False,
          "notes": True
        }
        """
        self.logger.debug('Returning default editing info for %s', obj.get_prepid())
        return {k: False for k in obj.get_json().keys()}

    def edit_allowed(self, old_obj, new_obj, changed_values):
        """
        Check whether done edit is allowed based on editing info
        and changed values
        """
        self.logger.debug('Checking if edit allowed for %s', new_obj.get_prepid())
        editing_info = self.get_editing_info(old_obj)
        if not editing_info:
            return True

        for changed_value in changed_values:
            changed_value_trimmed = changed_value.split('.')[0].split('[')[0]
            allowed = editing_info.get(changed_value_trimmed, False)
            if not allowed:
                raise Exception(f'It is not allowed to change value of "{changed_value_trimmed}"')

        return True

    def get_changes(self, reference, target, prefix=None, changed_values=None):
        """
        Get dictionary of different values across two objects
        """
        if changed_values is None:
            changed_values = []

        if prefix is None:
            prefix = ''

        if isinstance(reference, ModelBase):
            reference = reference.get_json()

        if isinstance(target, ModelBase):
            target = target.get_json()

        if isinstance(reference, dict) and isinstance(target, dict):
            # Comparing two dictionaries
            keys = set(reference.keys()).union(set(target.keys()))
            for key in keys:
                self.get_changes(reference.get(key),
                                 target.get(key),
                                 '%s.%s' % (prefix, key),
                                 changed_values)
        elif isinstance(reference, list) and isinstance(target, list):
            # Comparing two lists
            if len(reference) != len(target):
                changed_values.append(prefix.lstrip('._'))
            else:
                for i in range(min(len(reference), len(target))):
                    self.get_changes(reference[i],
                                     target[i],
                                     '%s[%s]' % (prefix, i),
                                     changed_values)
        else:
            # Comparing two values
            if reference != target:
                changed_values.append(prefix.lstrip('._'))

        return changed_values

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