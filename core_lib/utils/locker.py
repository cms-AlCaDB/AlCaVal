"""
Module that contains Locker class
"""
from threading import RLock, current_thread
import logging


class Locker():
    """
    Locker objects has a shared dictionary with locks in it
    Dictionary keys are strings
    """

    __locks = {}
    __locker_lock = RLock()

    def __init__(self):
        self.logger = logging.getLogger()

    def get_nonblocking_lock(self, prepid, info=''):
        """
        Return a non blocking lock or throw LockedException
        """
        lock = self.get_lock(prepid, info)
        # If we do a plus one
        if not lock.acquire(blocking=False):
            raise LockedException(f'Object "{prepid}" is curretly locker by other process')

        # We have to subtract one
        lock.release()
        return lock

    def get_lock(self, prepid, info=''):
        """
        Return a lock for a given prepid
        It can be either existing one or a new one will be created
        """
        with Locker.__locker_lock:
            lock = Locker.__locks.get(prepid, {'lock': RLock()})['lock']
            Locker.__locks[prepid] = {'lock': lock,
                                    'info': info}

            # If there are more than 99 locks in the system, do a cleanup
            if len(Locker.__locks) > 99:
                for key in list(Locker.__locks.keys()):
                    if key == prepid:
                        continue

                    if 'count=0' in str(Locker.__locks[key]['lock']):
                        self.logger.debug('Removing %s from locks dictionary', key)
                        del Locker.__locks[key]

        self.logger.debug('Returning a lock for %s. Thread %s',
                          prepid,
                          str(current_thread()))

        return lock

    def get_status(self):
        """
        Return dictionary of all locks and their statuses and infos
        """
        status = {k: {'l': str(v['lock']), 'i': v['info']} for k, v in Locker.__locks.items()}
        self.logger.debug('Lock status %s', status)
        return status


class LockedException(Exception):
    """
    Exception that should be thrown if nonblocking lock could not be acquired
    """
