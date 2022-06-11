"""
Module that contains all system APIs
"""
import time
import os.path
from core_lib.api.api_base import APIBase
from core_lib.utils.locker import Locker
from database.database import Database
from core_lib.utils.user_info import UserInfo
from .utils.submitter import RequestSubmitter


class SubmissionWorkerStatusAPI(APIBase):
    """
    Endpoint for getting submission workers status
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all request submission workers
        """
        status = RequestSubmitter().get_worker_status()
        return self.output_text({'response': status, 'success': True, 'message': ''})


class SubmissionQueueAPI(APIBase):
    """
    Endpoint for getting names in submission queue
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all request submission workers
        """
        status = RequestSubmitter().get_names_in_queue()
        return self.output_text({'response': status, 'success': True, 'message': ''})


class LockerStatusAPI(APIBase):
    """
    Endpoint for getting status of all locks in the system
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('administrator')
    def get(self):
        """
        Get status of all locks in the system
        """
        status = Locker().get_status()
        status = {k: ('count=0' not in v['l']) for k, v in status.items()}
        return self.output_text({'response': status, 'success': True, 'message': ''})


class UserInfoAPI(APIBase):
    """
    Endpoint for getting user information
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all locks in the system
        """
        user_info = UserInfo().get_user_info()
        return self.output_text({'response': user_info, 'success': True, 'message': ''})


class ObjectsInfoAPI(APIBase):
    """
    Endpoint for getting database information
    """

    def __init__(self):
        APIBase.__init__(self)

    def get_relvals(self):
        """
        Return summary of RelVals by status and submitted RelVals by CMSSW and batch name
        """
        start_time = time.time()
        collection = Database('relvals').collection
        status_query = [{'$match': {'deleted': {'$ne': True}}},
                        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}]
        by_status = collection.aggregate(status_query)

        batch_query = [{'$match': {'deleted': {'$ne': True}}},
                       {'$match': {'status': 'submitted'}},
                       {'$group': {'_id': {'release': '$cmssw_release', 'batch': '$batch_name'},
                                   'counts': {'$sum': 1}}},
                       {'$group': {"_id": "$_id.release",
                                   "batches": {"$push": {"batch_name": "$_id.batch",
                                                         "count": "$counts"}}}}]
        by_batch = collection.aggregate(batch_query)
        by_status = list(by_status)
        by_batch = list(by_batch)
        by_batch = sorted(by_batch, key=lambda x: x['_id'], reverse=True)
        for release in by_batch:
            release['batches'] = sorted(release['batches'],
                                        key=lambda x: (x['count'], x['batch_name'].lower()),
                                        reverse=True)

        statuses = ['new', 'approved', 'submitting', 'submitted', 'done', 'archived']
        by_status = sorted(by_status, key=lambda x: statuses.index(x['_id']))
        end_time = time.time()
        self.logger.debug('Getting objects info - RelVals, time taken %.2fs',
                          end_time - start_time)
        return by_status, by_batch

    def get_tickets(self):
        """
        Return summary of tickets by status and new tickets by CMSSW and batch name
        """
        start_time = time.time()
        collection = Database('tickets').collection
        status_query = [{'$match': {'deleted': {'$ne': True}}},
                        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}]
        by_status = collection.aggregate(status_query)

        batch_query = [{'$match': {'deleted': {'$ne': True}}},
                       {'$match': {'status': 'new'}},
                       {'$group': {'_id': {'release': '$cmssw_release', 'batch': '$batch_name'},
                                   'counts': {'$sum': 1}}},
                       {'$group': {"_id": "$_id.release",
                                   "batches": {"$push": {"batch_name": "$_id.batch",
                                                         "count": "$counts"}}}}]

        by_batch = collection.aggregate(batch_query)
        by_status = list(by_status)
        by_batch = list(by_batch)
        by_batch = sorted(by_batch, key=lambda x: x['_id'], reverse=True)
        for release in by_batch:
            release['batches'] = sorted(release['batches'],
                                        key=lambda x: (x['count'], x['batch_name'].lower()),
                                        reverse=True)

        statuses = ['new', 'done']
        by_status = sorted(by_status, key=lambda x: statuses.index(x['_id']))
        end_time = time.time()
        self.logger.debug('Getting objects info - Tickets, time taken %.2fs',
                          end_time - start_time)
        return by_status, by_batch

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get number of RelVals with each status and processing strings of submitted requests
        """
        relvals_by_status, relvals_by_batch = self.get_relvals()
        tickets_by_status, tickets_by_batch = self.get_tickets()
        return self.output_text({'response': {'relvals' : {'by_status': relvals_by_status,
                                                           'by_batch': relvals_by_batch},
                                              'tickets' : {'by_status': tickets_by_status,
                                                           'by_batch': tickets_by_batch}},
                                 'success': True,
                                 'message': ''})


class BuildInfoAPI(APIBase):
    """
    Endpoint for getting build information if it is available
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get build version if release_timestamp file exists
        """
        build_version = 'unavailable'
        if os.path.isfile('release_timestamp'):
            with open('release_timestamp') as timestamp_file:
                build_version = timestamp_file.read()

        return self.output_text({'response': build_version, 'success': True, 'message': ''})


class UptimeInfoAPI(APIBase):
    """
    Endpoint for getting uptime information
    """

    start_time = time.time()

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get number of seconds since start
        """
        uptime = int(time.time() - self.start_time)
        seconds = uptime
        days = int(seconds / 86400)
        seconds -= days * 86400
        hours = int(seconds / 3600)
        seconds -= hours * 3600
        minutes = int(seconds / 60)
        seconds -= minutes * 60
        return self.output_text({'response': {'uptime': uptime,
                                              'days': days,
                                              'hours': hours,
                                              'minutes': minutes,
                                              'seconds': seconds},
                                 'success': True,
                                 'message': ''})