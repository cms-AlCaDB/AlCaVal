from flask import url_for, Markup
from flask_table import Table, Col, LinkCol, html

class DatasetCol(Col):
    def td_format(self, content):
        return f"<a target='_blank' rel='noopener noreferrer' href='https://cmsweb.cern.ch/das/request?input={content}'>{content}</a>"

class DQMLinkCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)
    def td_format(self, content, item):
        s1 = 'https://cmsweb.cern.ch/dqm/dev/start?runnr=%s;' % item['run_number']
        s3 = 'workspace=Everything'
        s4 = 'referencepos=ratiooverlay;referenceshow=all;referencenorm=True;'
        s2 = 'dataset=%s;' % item['dataset']
        link = s1 + s2 + s3
        return f"<a target='_blank' rel='noopener noreferrer' href='{link}'>Link</a>"

class DQMTable(Table):
    dataset = DatasetCol("Dataset", td_html_attrs={'style': 'white-space: nowrap'})

    # prepid = LinkCol('Prep ID', endpoint='relvals.get_relval', 
    #                 url_kwargs=dict(prepid='prepid'), 
    #                 anchor_attrs={'class': 'myclass'}, attr='prepid',
    #                 td_html_attrs={'style': 'white-space: nowrap'}
    #                 )
    status = Col('Status')
    dqmlink = DQMLinkCol("DQM Link", td_html_attrs={'style': 'white-space: nowrap'})
    # SourceDQM = DQMLinkCol("Original DQM Link", td_html_attrs={'style': 'white-space: nowrap'})
    run_number = Col('Run Number')

    jira_ticket = LinkCol('Jira', endpoint='dqm.dqm_plots', 
                            url_kwargs=dict(jira_ticket='jira_ticket'), 
                            anchor_attrs={}, attr='jira_ticket',
                            td_html_attrs={'style': 'white-space: nowrap'}
                            )

    # ticket = LinkCol('Ticket', endpoint='tickets.tickets', 
    #                 url_kwargs=dict(prepid='ticket'), 
    #                 anchor_attrs={}, attr='ticket',
    #                 td_html_attrs={'style': 'white-space: nowrap'}
    #                 )


    relval = LinkCol('Relval', endpoint='relvals.get_relval', 
                    url_kwargs=dict(prepid='relval'), 
                    anchor_attrs={}, attr='relval',
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    allow_sort = False
    table_id = 'dqmplot_list'
    allow_empty = True

    #Atrributes
    html_attrs = {"style":"margin-left: 0px; width: 100%;"}
    thead_attrs = {'style': 'white-space: nowrap'}
