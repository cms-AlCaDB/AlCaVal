"""
Module that contains all search APIs
"""
import re
import time
import flask
from core_lib.api.api_base import APIBase
from database.database import Database
from .model.ticket import Ticket
from .model.relval import RelVal


class SearchAPI(APIBase):
    """
    Endpoint that is used for search in the database
    """

    def __init__(self):
        APIBase.__init__(self)
        self.classes = {'tickets': Ticket,
                        'relvals': RelVal,
                        'relval-tests': RelVal,}

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Perform a search
        """
        args = flask.request.args.to_dict()
        if args is None:
            args = {}

        db_name = args.pop('db_name', None)
        page = int(args.pop('page', 0))
        limit = int(args.pop('limit', 2000))
        sort = args.pop('sort', None)
        sort_asc = args.pop('sort_asc', None)

        # Special cases
        from_ticket = args.pop('ticket', None)
        if db_name == 'relvals' and from_ticket:
            ticket_database = Database('tickets')
            tickets = ticket_database.query(query_string=f'prepid={from_ticket}',
                                            limit=100,
                                            ignore_case=True)
            created_relvals = []
            for ticket in tickets:
                created_relvals.extend(ticket['created_relvals'])

            created_relvals = ','.join(created_relvals)
            prepid_query = args.pop('prepid', '')
            args['prepid'] = ('%s,%s' % (prepid_query, created_relvals)).strip(',')

        # Sorting logic: by default sort dsc by cration time
        if sort is None:
            sort = 'created_on'

        if sort == 'created_on' and sort_asc is None:
            sort_asc = False

        if sort_asc is None:
            sort_asc = True

        limit = max(1, min(limit, 500))
        sort_asc = str(sort_asc).lower() == 'true'
        query_string = '&&'.join(['%s=%s' % (pair) for pair in args.items()])
        database = Database(db_name)
        query_string = database.build_query_with_types(query_string, self.classes[db_name])
        results, total_rows = database.query_with_total_rows(query_string=query_string,
                                                             page=page,
                                                             limit=limit,
                                                             sort_attr=sort,
                                                             sort_asc=sort_asc,
                                                             ignore_case=True)

        return self.output_text({'response': {'results': results,
                                              'total_rows': total_rows},
                                 'success': True,
                                 'message': ''})


class SuggestionsAPI(APIBase):
    """
    Endpoint that is used to fetch suggestions
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Return a list of prepid suggestions for given query
        """
        args = flask.request.args.to_dict()
        if args is None:
            args = {}

        db_name = args.pop('db_name', None)
        query = args.pop('query', None).replace(' ', '.*')
        limit = max(1, min(50, args.pop('limit', 20)))

        if not db_name or not query:
            raise Exception('Bad db_name or query parameter')

        database = Database(db_name)
        db_query = {'prepid': re.compile(f'.*{query}.*', re.IGNORECASE)}
        results = database.collection.find(db_query).limit(limit)
        results = [x['prepid'] for x in results]

        return self.output_text({'response': results,
                                 'success': True,
                                 'message': ''})


class WildSearchAPI(APIBase):
    """
    Endpoint that is used for abstract search in the whole database
    """

    def __init__(self):
        APIBase.__init__(self)
        self.classes = {'tickets': Ticket,
                        'relvals': RelVal}

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Perform a search
        """
        args = flask.request.args.to_dict()
        if args is None:
            args = {}

        query = args.pop('q', None)
        if not query:
            return self.output_text({'response': [],
                                     'success': True,
                                     'message': 'Query string too short'})

        query = query.strip().replace(' ', '*')
        if len(query) < 3:
            return self.output_text({'response': [],
                                     'success': True,
                                     'message': 'Query string too short'})

        tickets_db = Database('tickets')
        relvals_db = Database('relvals')

        attempts = [('relvals', relvals_db, 'prepid', False),
                    ('tickets', tickets_db, 'prepid', False),
                    ('relvals', relvals_db, 'prepid', True),
                    ('tickets', tickets_db, 'prepid', True),
                    # Tickets
                    ('tickets', tickets_db, 'cmssw_release', True),
                    ('tickets', tickets_db, 'batch_name', True),
                    ('tickets', tickets_db, 'workflows', False),
                    ('tickets', tickets_db, 'label', True),
                    ('tickets', tickets_db, 'created_relvals', True),
                    # Requests
                    ('relvals', relvals_db, 'cmssw_release', True),
                    ('relvals', relvals_db, 'batch_name', True),
                    ('relvals', relvals_db, 'workflow_id', False),
                    ('relvals', relvals_db, 'workflow_name', True),
                    ('relvals', relvals_db, 'output_dataset', True),
                    ('relvals', relvals_db, 'workflow', True),]

        results = []
        used_values = set()
        for attempt in attempts:
            db_name = attempt[0]
            database = attempt[1]
            attr = attempt[2]
            wrap_in_wildcards = attempt[3]
            if wrap_in_wildcards:
                wrapped_query = f'*{query}*'
            else:
                wrapped_query = f'{query}'

            self.logger.info('Trying to query %s in %s', wrapped_query, db_name)
            try:
                typed_query = database.build_query_with_types(f'{attr}={wrapped_query}',
                                                              self.classes[db_name])
                query_results = database.query(typed_query, 0, 5, ignore_case=True)
            except ValueError:
                # In case text input was casted to a number
                continue

            for result in query_results:
                values = self.extract_values(result, attr, wrapped_query, db_name)
                for value in values:
                    key = f'{db_name}:{attr}:{value}'
                    if key not in used_values:
                        used_values.add(key)
                        results.append({'value': value,
                                        'attribute': attr,
                                        'database': db_name,
                                        'document': result})

            # Limit results to 20 to save DB some queries
            if len(results) >= 20:
                results = results[:20]
                break

            # Limit DB query rate as this is very expensive
            time.sleep(0.075)

        return self.output_text({'response': results,
                                 'success': True,
                                 'message': ''})

    def extract_values(self, item, attribute, query, db_name):
        """
        Return a list of one or multiple values got from an object
        One object might have multiple values, e.g. output datasets
        """
        if db_name == 'tickets' and attribute == 'workflows':
            for workflow in item['workflow_ids']:
                if workflow == float(query):
                    return [str(workflow)]

        elif db_name == 'relvals' and attribute == 'workflow_id':
            if item['workflow_id'] == float(query):
                return [str(item['workflow_id'])]

        if attribute in item and attribute not in ('created_relvals', ):
            return [item[attribute]]

        values = []
        matcher = re.compile(query.replace('*', '.*'), re.IGNORECASE)
        self.logger.info('Item: %s, attribute: %s, query: %s, db name: %s',
                         item['prepid'],
                         attribute,
                         query,
                         db_name)

        if db_name == 'relvals':
            if attribute == 'output_dataset':
                for dataset in item['output_datasets']:
                    if matcher.fullmatch(dataset):
                        values.append(dataset)

            elif attribute == 'workflow':
                for workflow in item['workflows']:
                    if matcher.fullmatch(workflow['name']):
                        values.append(workflow['name'])
        elif db_name == 'tickets':
            if attribute == 'created_relvals':
                for relval in item['created_relvals']:
                    if matcher.fullmatch(relval):
                        values.append(relval)

        return values