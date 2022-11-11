from flask import url_for, Markup
from flask_table import Table, Col, LinkCol, html

class DatasetCol(Col):
    def td_format(self, content):
        return f"<a target='_blank' rel='noopener noreferrer' href='https://cmsweb.cern.ch/das/request?input={content}'>{content}</a>"

class DQMLinkCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)
    def td_format(self, content, item):
        s1 = 'https://cmsweb.cern.ch/dqm/dev/start?runnr=%s;' % item['run_number'][0]
        s2 = 'dataset=%s;' % item['dataset']
        s3 = 'sampletype=offline_data;filter=all;referencepos=overlay;referenceshow=customise;referencenorm=True;search=;striptype=object;stripruns=;stripaxis=run;stripomit=none;workspace=Everything;size=M;root=;focus=;zoom=no;'
        link = s1 + s2 + s3
        title = f"Dataset: {item['dataset']}"
        return f"<a target='_blank' rel='noopener noreferrer' href='{link}' title='{title}'>DQM</a>"

class OverlayLinkCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)
    def td_format(self, content, item):
        s1 = 'https://cmsweb.cern.ch/dqm/dev/start?runnr=%s;' % item['run_number'][0]
        s2 = 'dataset=%s;' % item['dataset']
        s3 = 'sampletype=offline_data;filter=all;referencepos=overlay;referenceshow=all;referencenorm=False;'
        s4 = f'referenceobj1=other%3A{item["run_number"][0]}%3A{item["reference"]}%3AReference%3A;'
        s5 = 'referenceobj2=none;referenceobj3=none;referenceobj4=none;search=;striptype=object;stripruns=;stripaxis=run;stripomit=none;workspace=Everything;size=M;root=;focus=;zoom=no;'
        link = s1 + s2 + s3 + s4 + s5
        title = f"Target: {item['dataset']}\nReference: {item.get('reference')}"
        return f"<a target='_blank' rel='noopener noreferrer' href='{link}' title='{title}'>Overlay</a>"

class OriginalLinkCol(Col):
    def __init__(self, name, attr=None, attr_list=None, text_fallback='', **kwargs):
        super(OriginalLinkCol, self).__init__(
                                            name,
                                            attr=attr,
                                            attr_list=attr_list,
                                            **kwargs
                                           )
        self.text_fallback = text_fallback

    def get_attr_list(self, attr):
        return super(OriginalLinkCol, self).get_attr_list(None)

    def text(self, item, attr_list):
        if attr_list:
            return self.from_attr_list(item, attr_list)
        elif self.text_fallback:
            return self.text_fallback
        else:
            return self.name

    def td_contents(self, item, attr_list):
        s1 = 'https://cmsweb.cern.ch/dqm/relval/start?runnr=%s;' % item['run_number'][0]
        s2 = 'dataset=%s;' % item['source']
        s5 = 'referenceobj2=none;referenceobj3=none;referenceobj4=none;search=;striptype=object;stripruns=;stripaxis=run;stripomit=none;workspace=Everything;size=M;root=;focus=;zoom=no;'
        link = s1 + s2 + s5
        attrs = {'target':'_blank', 'rel':'noopener noreferrer', 'href':f'{link}',
                 'title': f"Dataset: {item['source']}"
                }
        Input = html.element('a', attrs=attrs, content='DQM', escape_content=False)
        return Input

class OriginalOverlayLinkCol(OriginalLinkCol):
    def td_contents(self, item, attr_list):
        s1 = 'https://cmsweb.cern.ch/dqm/relval/start?runnr=%s;' % item['run_number'][0]
        s2 = 'dataset=%s;' % item['source']
        s3 = 'sampletype=offline_data;filter=all;referencepos=overlay;referenceshow=all;referencenorm=False;'
        s4 = f'referenceobj1=other%3A{item["run_number"][0]}%3A{item["compared_with"]}%3AReference%3A;'
        s5 = 'referenceobj2=none;referenceobj3=none;referenceobj4=none;search=;striptype=object;stripruns=;stripaxis=run;stripomit=none;workspace=Everything;size=M;root=;focus=;zoom=no;'
        link = s1 + s2 + s3 + s4 + s5
        attrs = {'target':'_blank', 'rel':'noopener noreferrer', 'href':f'{link}',
                 'title': f"Target: {item['source']},\nReference: {item['compared_with']}"
                }
        Input = html.element('a', attrs=attrs, content='Overlay', escape_content=False)
        return Input

class DQMTable(Table):
    relval = LinkCol('Relval', endpoint='relvals.get_relval',
                    url_kwargs=dict(prepid='relval'),
                    anchor_attrs={}, attr='relval',
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )
    status = Col('Status')
    jira_ticket = LinkCol('Jira', endpoint='dqm.dqm_plots', 
                            url_kwargs=dict(jira_ticket='jira_ticket'), 
                            anchor_attrs={}, attr='jira_ticket',
                            td_html_attrs={'style': 'white-space: nowrap'}
                            )
    dqmlink = DQMLinkCol("Compared DQM plots", td_html_attrs={'style': 'white-space: nowrap'})
    overlay_plots = OverlayLinkCol("Compared overlay plots", td_html_attrs={'style': 'white-space: nowrap'})
    orignal_dqm = OriginalLinkCol('Original DQM plots', text_fallback='')
    orignal_dqm_overlay = OriginalOverlayLinkCol('Original overlay plots', text_fallback='')
    run_number = Col('Run Number')
    dataset = DatasetCol("Compared dataset", td_html_attrs={'style': 'white-space: nowrap'})

    # ticket = LinkCol('Ticket', endpoint='tickets.tickets', 
    #                 url_kwargs=dict(prepid='ticket'), 
    #                 anchor_attrs={}, attr='ticket',
    #                 td_html_attrs={'style': 'white-space: nowrap'}
    #                 )

    allow_sort = False
    table_id = 'dqmplot_list'
    allow_empty = True

    #Atrributes
    html_attrs = {"style":"margin-left: 0px; width: 100%;"}
    thead_attrs = {'style': 'white-space: nowrap'}
