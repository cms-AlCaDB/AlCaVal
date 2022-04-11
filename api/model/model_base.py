"""
Module that contains ModelBase class
"""
import json
import logging
import re
import time
from copy import deepcopy
from ..utils.user_info import UserInfo
from ..utils.common_utils import clean_split


class ModelBase():
    """
    Base class for all model objects
    Has some convenience methods as well as somewhat smart setter
    Contains a bunch of sanity checks
    """
    __schema = {}
    __logger = logging.getLogger()
    default_lambda_checks = {}
    lambda_checks = {}

    def __init__(self, json_input=None, check_attributes=True):
        self.__json = {}
        self.logger = ModelBase.__logger
        self.__class_name = self.__class__.__name__

        self.initialized = False
        if json_input is None:
            json_input = self.schema()
            check_attributes = False

        if check_attributes:
            self.logger.debug('Creating %s object. JSON input present: %s',
                              self.__class_name,
                              'YES' if json_input else 'NO')
            self.__fill_values(json_input, check_attributes)
        else:
            self.logger.debug('Using JSON input for %s', self.__class_name)
            self.__json = json_input

        self.initialized = True

    def __fill_values(self, json_input, check_attributes=True):
        """
        Copy values from given dictionary to object's json
        Initialize default values from schema if any are missing
        """
        if json_input:
            if 'prepid' in self.__schema or '_id' in self.__schema:
                prepid = json_input.get('prepid')
                if not prepid:
                    raise Exception('PrepID cannot be empty')

                self.set('prepid', prepid)

        ignore_keys = set(['_id', 'prepid'])
        keys = set(self.__schema.keys())
        if json_input:
            # Just to show errors if any incorrect keys are passed
            bad_keys = set(json_input.keys()) - keys - ignore_keys
            if bad_keys:
                self.logger.warning('Keys that are not in schema of %s: %s',
                                    self.__class_name,
                                    ', '.join(bad_keys))
                # raise Exception(f'Invalid key "{", ".join(bad_keys)}" for {self.__class_name}')

        self.__fill_values_dict(self.__json, json_input, self.__schema, '', check_attributes)

    def __set(self, attribute, target_dict, value, check=True):
        prepid = self.get_prepid()
        attribute = attribute.strip('.')
        attribute_in_schema = self.__attribute_in_schema(attribute)
        if not isinstance(value, type(attribute_in_schema)):
            self.logger.debug('%s of %s is not expected (%s) type (got %s). Will try to cast',
                              attribute,
                              prepid,
                              type(attribute_in_schema),
                              type(value))
            value = self.cast_value_to_correct_type(attribute, value)

        if isinstance(value, str):
            value = value.strip()

        if check and not self.check_attribute(attribute, value):
            self.logger.error('Invalid value "%s" for key "%s" for object %s of type %s',
                              value,
                              attribute,
                              prepid,
                              self.__class_name)
            raise Exception(f'Invalid {attribute} value {value} for {prepid}')

        target_dict[attribute.split('.')[-1]] = value

    def __fill_values_dict(self, target_dict, source_dict, schema_dict, attribute_prefix, check):
        attribute_prefix = attribute_prefix.strip('.')

        for key, default_value in schema_dict.items():
            if key == '_id':
                continue

            # Default value here is another dict from schema
            # It will be used not as value, but as new schema
            if isinstance(default_value, dict) and default_value:
                target_dict[key] = {}
                self.__fill_values_dict(target_dict[key],
                                        source_dict.get(key, {}),
                                        default_value,
                                        f'{attribute_prefix}.{key}',
                                        check)
            elif key not in source_dict:
                target_dict[key] = default_value
            else:
                self.__set(f'{attribute_prefix}.{key}',
                           target_dict,
                           source_dict[key],
                           check)

    def set(self, attribute, value=None):
        """
        Set attribute of the object
        """
        if not attribute:
            raise Exception('Attribute name not specified')

        attribute = attribute.strip('.')
        self.__set(attribute, self.__json, value)
        if attribute == 'prepid':
            self.__json['_id'] = value

        return self.__json

    def __attribute_in_schema(self, attribute_name):
        schema = self.__schema
        attribute_path = clean_split(attribute_name, '.')
        for attribute in attribute_path:
            if attribute not in schema:
                raise Exception(f'Attribute {attribute_name} could not be '
                                f'found in {self.__class_name} schema')

            schema = schema[attribute]

        return schema

    def get(self, attribute):
        """
        Get attribute of the object
        """
        if not attribute:
            raise Exception('Attribute name not specified')

        self.__attribute_in_schema(attribute)

        return self.__json[attribute]

    def get_prepid(self):
        """
        Return prepid or _id if any of it exist
        Return none if it doesn't
        """
        if 'prepid' in self.__json:
            return self.__json['prepid']

        if '_id' in self.__json:
            return self.__json['_id']

        return None

    def check_attribute(self, attribute_name, attribute_value):
        """
        This method must return whether given value of attribute is valid
        or raise exception with error
        First it tries to find exact name match in lambda functions
        Then it checks for lambda function with double underscore prefix which
        indicates that this is a list of values
        """
        if attribute_name in self.lambda_checks:
            if not self.lambda_checks[attribute_name](attribute_value):
                return False

        # List
        if f'__{attribute_name}' in self.lambda_checks:
            if not isinstance(attribute_value, list):
                raise Exception(f'Expected {attribute_name} to be a list')

            lambda_check = self.lambda_checks[f'__{attribute_name}']
            for item in attribute_value:
                if not lambda_check(item):
                    raise Exception(f'Bad {attribute_name} value "{item}"')

        # Dict
        if f'_{attribute_name}' in self.lambda_checks:
            if not isinstance(attribute_value, dict):
                raise Exception(f'Expected {attribute_name} to be a dict')

            lambda_checks = self.lambda_checks[f'_{attribute_name}']
            invalid_keys = set(attribute_value.keys()) - set(lambda_checks.keys())
            if invalid_keys:
                raise Exception(f'Keys {",".join(invalid_keys)} are not '
                                f'allowed in {attribute_name}')

            for key, lambda_check in lambda_checks.items():
                value = attribute_value[key]
                if not lambda_check(value):
                    raise Exception(f'Bad {key} value "{value}" in {attribute_name} dictionary')

        return True

    def cast_value_to_correct_type(self, attribute_name, attribute_value):
        """
        If value is not correct type, try to cast it to
        correct type according to schema
        """
        expected_type = type(self.__attribute_in_schema(attribute_name))
        got_type = type(attribute_value)
        if expected_type == list and got_type == str:
            return [x.strip() for x in attribute_value.split(',') if x.strip()]

        prepid = self.get_prepid()
        expected_type_name = expected_type.__name__
        got_type_name = got_type.__name__
        try:
            return expected_type(attribute_value)
        except Exception as ex:
            self.logger.error(ex)
            raise Exception(f'Object {prepid} attribute {attribute_name} is wrong type. '
                            f'Expected {expected_type_name}, got {got_type_name}. '
                            f'It cannot be automatically casted to correct type')

    @classmethod
    def matches_regex(cls, value, regex):
        """
        Check if given string fully matches given regex
        """
        matcher = re.compile(regex)
        match = matcher.fullmatch(value)
        if match:
            return True

        return False

    def __get_json(self, item):
        """
        Internal method to recursively create dict representations of objects
        """
        if isinstance(item, ModelBase):
            return item.get_json()

        if isinstance(item, list):
            new_list = []
            for element in item:
                new_list.append(self.__get_json(element))

            return new_list

        return item

    def get_json(self):
        """
        Return JSON of the object
        """
        built_json = {}
        for attribute, value in self.__json.items():
            built_json[attribute] = self.__get_json(value)

        return deepcopy(built_json)

    @classmethod
    def schema(cls):
        """
        Return a copy of scema
        """
        return deepcopy(cls.__schema)

    def __str__(self):
        """
        String representation of the object
        """
        object_json = self.get_json()
        if 'history' in object_json:
            del object_json['history']

        return (f'Object ID: {self.get_prepid()}\n'
                f'Type: {self.__class_name}\n'
                f'Dict: {json.dumps(object_json, indent=2, sort_keys=True)}')

    def add_history(self, action, value, user, timestamp=None):
        """
        Add entry to object's history
        If no time is specified, use current time
        """
        if user is None:
            user = UserInfo().get_username()

        history = self.get('history')
        history.append({'action': action,
                        'time': int(timestamp if timestamp else time.time()),
                        'user': user,
                        'value': value})
        self.set('history', history)

    @classmethod
    def lambda_check(cls, name):
        """
        Return a lambda check from default lambda checks dictionary
        """
        return cls.default_lambda_checks.get(name)
