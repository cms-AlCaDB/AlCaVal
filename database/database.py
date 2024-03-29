"""
A module that handles all communication with MongoDB
"""
import logging
import time
import json
import os
import re
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT


class Database():
    """
    Database class represents a particular collection in MongoDB
    """

    DATABASE_HOST = 'localhost'
    DATABASE_PORT = 27017
    DATABASE_NAME = None
    SEARCH_RENAME = {}
    USERNAME = None
    PASSWORD = None

    def __init__(self, collection_name=None):
        """
        Constructor of database interface
        """
        self.collection_name = collection_name
        self.logger = logging.getLogger()
        db_host = os.environ.get('DB_HOST', Database.DATABASE_HOST)
        db_port = int(os.environ.get('DB_PORT', Database.DATABASE_PORT))
        if not Database.DATABASE_NAME:
            raise Exception('Database name is not set')

        if Database.USERNAME and Database.PASSWORD:
            self.logger.debug('Using DB with username and password. DB: %s', collection_name)
            self.client = MongoClient(db_host,
                                      db_port,
                                      username=Database.USERNAME,
                                      password=Database.PASSWORD,
                                      authSource='admin',
                                      authMechanism='SCRAM-SHA-256')[Database.DATABASE_NAME]
        else:
            self.logger.debug('Using DB without username and password')
            self.client = MongoClient(db_host, db_port)[Database.DATABASE_NAME]

        self.collection = self.client[collection_name]

    @staticmethod
    def set_host_port(host, port):
        """
        Set global database hostname and port
        """
        Database.DATABASE_HOST = host
        Database.DATABASE_PORT = port

    @staticmethod
    def set_database_name(database_name):
        """
        Set global database name
        """
        Database.DATABASE_NAME = database_name

    @staticmethod
    def add_search_rename(collection, value, renamed_value):
        """
        Add a global rename rule to query method
        """
        if collection not in Database.SEARCH_RENAME:
            Database.SEARCH_RENAME[collection] = {}

        Database.SEARCH_RENAME[collection][value] = renamed_value

    @staticmethod
    def set_credentials(username, password):
        """
        Set database username and password
        """
        Database.USERNAME = username
        Database.PASSWORD = password

    @staticmethod
    def set_credentials_file(filename):
        """
        Load credentials from a JSON file
        """
        with open(filename) as json_file:
            credentials = json.load(json_file)

        Database.set_credentials(credentials['username'], credentials['password'])

    def get_count(self):
        """
        Get number of documents in the database
        """
        return self.collection.count_documents({})

    def get(self, document_id):
        """
        Get a single document with given identifier
        """
        result = self.collection.find_one({'_id': document_id})
        if result and 'last_update' in result:
            del result['last_update']

        return result

    def document_exists(self, document_id):
        """
        Do a GET request to check whether document exists
        """
        response = self.get(document_id)
        return bool(response)

    def delete_document(self, document, purge=False):
        """
        Delete a document
        It does not actually delete a document, just removes all attributes
        except _id and marks it as "deleted"
        If purge is set to True, then document is actually removed from DB
        """
        if not isinstance(document, dict):
            self.logger.error('%s is not a dictionary', document)
            return False

        document_id = document.get('_id', '')
        document_id = document_id.strip()
        if not document_id:
            self.logger.error('%s does not have a _id', document)
            return False

        if purge:
            return self.collection.delete_one({'_id': document_id})

        deleted_document = {'_id': document_id,
                            'deleted': True}
        return self.save(deleted_document)

    def save(self, document):
        """
        Save a document
        """
        if not isinstance(document, dict):
            self.logger.error('%s is not a dictionary', document)
            return False

        document_id = document.get('_id', '')
        if not document_id:
            self.logger.error('%s does not have a _id', document)
            return False

        document['last_update'] = int(time.time())
        if self.document_exists(document_id):
            self.logger.debug('Updating %s', document_id)
            return self.collection.replace_one({'_id': document_id}, document)

        self.logger.debug('Creating %s', document_id)
        return self.collection.insert_one(document)

    def query(self,
              query_string=None,
              page=0, limit=20,
              sort_attr=None, sort_asc=True,
              include_deleted=False,
              ignore_case=False):
        """
        Same as query_with_total_rows, but return only list of objects
        """
        return self.query_with_total_rows(query_string,
                                          page,
                                          limit,
                                          sort_attr,
                                          sort_asc,
                                          include_deleted,
                                          ignore_case)[0]

    def get_value_condition(self, value):
        """
        Get a condition from value and return value and condition separately
        """
        value_condition = None
        if '<' in value[0]:
            value_condition = '$lt'
            value = value[1:]
        elif value[0] == '>':
            value_condition = '$gt'
            value = value[1:]
        elif value[0] == '!':
            value_condition = '$ne'
            value = value[1:]

        self.logger.debug('Value: %s, condition: %s', value, value_condition)
        return value, value_condition

    def get_value_query(self, key, values, ignore_case=False):
        """
        Check for < > and ! in front of values, handle OR operation, use correct attribute type
        """
        value_or = []
        for value in values:
            value, value_condition = self.get_value_condition(value.strip())
            if '<int>' in key:
                value = int(value)
                if value_condition:
                    value = {value_condition: value}

                value_or.append({key.replace('<int>', ''): value})
            elif '<float>' in key:
                value = float(value)
                if value_condition:
                    value = {value_condition: value}

                value_or.append({key.replace('<float>', ''): value})
            elif '<bool>' in key:
                value = bool(value.lower() in ('true', 'yes'))
                if value_condition:
                    value = {value_condition: value}

                value_or.append({key.replace('<bool>', ''): value})
            else:
                if value_condition:
                    value = {value_condition: value}
                    value_or.append({key: value})
                else:
                    if '*' in value:
                        if ignore_case:
                            value = re.compile(f'^{value}$', re.IGNORECASE)

                        value_or.append({key: {'$regex': value}})
                    else:
                        if ignore_case:
                            value = re.compile(f'^{value}$', re.IGNORECASE)

                        value_or.append({key: value})

        self.logger.debug('Key: %s, values: %s, query: %s', key, values, value_or)
        if len(value_or) > 1:
            return {'$or': value_or}

        if len(value_or) == 1:
            return value_or[0]

        return None

    def query_with_total_rows(self,
                              query_string=None,
                              page=0, limit=20,
                              sort_attr=None, sort_asc=True,
                              include_deleted=False,
                              ignore_case=False,
                              wild_filter=False):
        """
        Perform a query in a database
        And operator is &&
        Example prepid=*19*&&is_root=false
        This is horrible, please think of something better
        """
        query_dict = {'$and': []}
        if not include_deleted:
            query_dict['$and'].append({'deleted': {'$ne': True}})

        if query_string:
            query_string_parts = [x for x in query_string.split('&&') if x.strip()]
            self.logger.debug('Query parts %s', query_string_parts)
            for part in query_string_parts:
                split_part = part.split('=')
                key = split_part[0].strip()
                if key == 'deleted':
                    # Prevent cheating
                    continue

                values = split_part[1].strip().replace('**', '*').replace('*', '.*')
                values = [value.strip() for value in values.split(',') if value.strip()]
                if not values:
                    # If no value is given, then no results will be returned
                    # For example "prepid=" shou return nothing
                    return [], 0

                value_query = self.get_value_query(key, values, ignore_case)
                if value_query:
                    query_dict['$and'].append(value_query)

        if wild_filter:
            # Create a list of queries that match the regex against each field
            query = rf".*{wild_filter}.*"
            queries = []
            for field_name in self.collection.find_one().keys():
                queries.append({field_name: {"$regex": re.compile(str(query))}})

            query = {"$or": queries}
            self.collection.create_index([("$**", TEXT)])
            query_dict['$and'].append(query)

        if len(query_dict['$and']) == 1:
            query_dict = query_dict['$and'][0]
        elif not query_dict['$and']:
            query_dict = {}

        if not sort_attr:
            sort_attr = '_id'
        elif sort_attr in Database.SEARCH_RENAME.get(self.collection_name, {}):
            sort_attr = Database.SEARCH_RENAME[self.collection_name][sort_attr]

        sort_attr = sort_attr.replace('<int>', '').replace('<float>', '').replace('<bool>', '')
        self.logger.debug('Database "%s" query dict %s', self.collection_name, query_dict)
        self.logger.debug('Sorting on %s ascending %s', sort_attr, 'YES' if sort_asc else 'NO')
        result = self.collection.find(query_dict)
        result = result.sort(sort_attr, ASCENDING if sort_asc else DESCENDING)
        total_rows = result.count()
        result = result.skip(page * limit).limit(limit)
        return list(result), int(total_rows)

    def build_query_with_types(self, query_string, object_class):
        """
        This is horrible, please think of something better
        """
        schema = object_class.schema()
        query_string_parts = [x.strip() for x in query_string.split('&&') if x.strip()]
        typed_arguments = []
        for part in query_string_parts:
            split_part = part.split('=')
            key = split_part[0]
            value = split_part[1]
            if key in Database.SEARCH_RENAME.get(self.collection_name, {}):
                key = Database.SEARCH_RENAME[self.collection_name][key]
            elif isinstance(schema.get(key), (int, float, bool)):
                key = f'{key}<{type(schema.get(key)).__name__}>'

            typed_arguments.append(f'{key}={value}')

        return '&&'.join(typed_arguments)
