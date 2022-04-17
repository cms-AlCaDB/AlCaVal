from flask import url_for
from flask_table import Table, Col, LinkCol


class ActionCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)

    def td_format(self, content, item):
        divAction = "<div class='actions'>{mylinks}</div>"
        edit = f"<a href='/tickets/edit?prepid={content}'>Edit</a>"
        clone = f"<a href='/tickets/edit?clone={content}'>Clone</a>"
        matrix = f"<a href='api/tickets/run_the_matrix/{content}'>runTheMatrix.py</a>"
        if item['status'] == 'new':
            delete = f"""<a class="delete_ticket delete_{content}" onclick="delete_ticket('{content}')" href="javascript:void(0);">Delete</a> """
            create_relval = f"""<a class="create_relval_id relval_{content}" onclick="create_relval('{content}');" href="javascript:void(0);">Create Relval</a>"""
            links = "".join([edit, clone, delete, create_relval, matrix])
            return divAction.format(mylinks=links)
        else:
            links = "".join([edit, clone, matrix])
            return divAction.format(mylinks=links)

class WFCol(Col):
    def td_format(self, content):
        workflows = ', '.join([str(a) for a in content])
        return f"<div class='bg-light'>{workflows}</div>"

class ItemTable(Table):
    prepid = LinkCol('Prep ID', endpoint='tickets.tickets', 
                    url_kwargs=dict(prepid='prepid'), 
                    anchor_attrs={'class': 'myclass'}, attr='prepid')

    status = Col('Status')

    _id = ActionCol("Actions", td_html_attrs={'style': 'white-space: nowrap'})

    cmssw_release = LinkCol('CMSSW Release', endpoint='tickets.tickets', 
                    url_kwargs=dict(cmssw_release='cmssw_release'), 
                    anchor_attrs={}, attr='cmssw_release')

    batch_name = LinkCol('Batch Name', endpoint='tickets.tickets', 
                    url_kwargs=dict(batch_name='batch_name'), 
                    anchor_attrs={}, 
                    attr='batch_name'
                )

    cpu_cores = Col('CPU Cores')

    label = Col('Label')

    memory = Col('Memory')

    scram_arch = Col('Scram Arch')

    workflow_ids = WFCol('Workflows', td_html_attrs={'style': 'white-space: nowrap'})

    allow_sort = False
    table_id = 'ticket_list'
    allow_empty = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction =  'desc'
        else:
            direction = 'asc'
        return url_for('tickets.tickets', sort=col_key, direction=direction)

    def get_tr_attrs(self, item):
        return {'id': item['prepid']}
