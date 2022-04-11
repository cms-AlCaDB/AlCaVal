from ..controller.controller_base import ControllerBase
from database.database import Database
from ..model.ticket import Ticket

class TicketController(ControllerBase):
    """
    Ticket controller performs all actions with tickets
    """
    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'tickets'
        self.model_class = Ticket

    def create(self, json_data):
        # Clean up the input
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        prepid_part = f'{cmssw_release}__{batch_name}'
        ticket_db = Database('tickets')
        json_data['prepid'] = f'{prepid_part}-00000'
        with self.locker.get_lock(f'generate-ticket-prepid-{prepid_part}'):
            # Get a new serial number
            serial_number = self.get_highest_serial_number(ticket_db,
                                                           f'{prepid_part}-*')
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            ticket = super().create(json_data)

        return ticket