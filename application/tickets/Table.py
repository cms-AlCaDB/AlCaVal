from flask import url_for
from flask_table import Table, Col, LinkCol


class LangCol(Col):
    def td_format(self, content):
        edit = f"<a href='/tickets/edit?prepid={content}'>Edit</a>"
        clone = f"<a href='/tickets/edit?clone={content}'>Clone</a>"
        matrix = f"<a href='api/tickets/run_the_matrix/{content}'>runTheMatrix.py</a>"
        output = " | ".join([edit, clone, matrix])
        return output

class ItemTable(Table):
    prepid = LinkCol('Prep ID', endpoint='tickets.tickets', 
                    url_kwargs=dict(prepid='prepid'), 
                    anchor_attrs={'class': 'myclass'}, attr='prepid')

    status = Col('Status')

    _id = LangCol("Actions", td_html_attrs={'style': 'white-space: nowrap'})

    cmssw_release = LinkCol('CMSSW Release', endpoint='tickets.tickets', 
                    url_kwargs=dict(cmssw_release='cmssw_release'), 
                    anchor_attrs={'class': 'myclass'}, attr='cmssw_release')

    batch_name = LinkCol('Batch Name', endpoint='tickets.tickets', 
                    url_kwargs=dict(batch_name='batch_name'), 
                    anchor_attrs={'class': 'myclass'}, 
                    attr='batch_name'
                )

    cpu_cores = Col('CPU Cores')

    label = Col('Label')

    memory = Col('Memory')

    scram_arch = Col('Scram Arch')

    workflow_ids = Col('Workflows')

    allow_sort = False
    
    allow_empty = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction =  'desc'
        else:
            direction = 'asc'
        return url_for('tickets.tickets', sort=col_key, direction=direction)