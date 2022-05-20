from datetime import datetime
from flask import url_for, Markup
from flask_table import Table, Col, LinkCol, html

class ActionCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)

    def td_format(self, content, item):
        divAction = "<div class='actions'>{mylinks}</div>"

        edit = f"<a class='cls_edit_relval' href='/relvals/edit?prepid={content}' title='Edit this relval'>Edit</a>"
        clone = f"<a class='cls_clone_relval' href='/relvals/edit?clone={content}' title='Clone this relval'>Clone</a>"
        cmsDriver = f"<a href='api/relvals/get_cmsdriver/{content}' title='Show cmsDriver.py commands for this relval'>cmsDriver</a>"
        job_dict = f"<a href='api/relvals/get_dict/{content}' title='Show job dict of ReqMgr2 workflow'>Job dict</a>"
        jira = f"<a href='https://its.cern.ch/jira/browse/{item['jira_ticket']}' title='Go to the Jira discussion {item['jira_ticket']}'>Jira</a>"
        create_jira = f"""<a class="cls_create_jira create_jira_{content}" onclick="create_jira('{content}')" href="javascript:void(0);" title='Create new Jira ticket'>Create Jira Ticket</a>"""
        jira = jira if item['jira_ticket'] != 'None' else create_jira

        prev_status = f"""<a class="cls_previous_status prevStatus_{content}" onclick="prevStatus(['{content}'])" href="javascript:void(0);" title='Move Relval to previous status'>Previous</a>"""
        prev_status = "" if item['status'] != 'new' else ""

        status_list = ['new', 'approved', 'submitting', 'submitted', 'done', 'archieved']
        new_status = status_list[status_list.index(item['status'])+1]
        next_status = f"""<a class="cls_next_status nextStatus_{content}" onclick="nextStatus(['{content}'])" href="javascript:void(0);" title='Move Relval to next status: from "{item['status']}" to "{new_status}"'>Next</a>"""
        next_status = next_status if item['status'] != 'done' else ""

        ticket = f"<a href='tickets?created_relvals={content}' title='Show a ticket from which this relval was created'>Ticket</a>"

        delete = f"""<a class="delete_relval delete_{content}" onclick="delete_relval(['{content}'])" href="javascript:void(0);" title='Delete relval'>Delete</a>"""
        delete = delete if item['status'] == 'new' else ""
        
        links = "".join([edit, clone, delete, cmsDriver, job_dict, jira, ticket, prev_status, next_status])
        return divAction.format(mylinks=links)

### Custom checkbox column class 
class CheckboxCol(Col):
    def __init__(self, name, attr=None, attr_list=None,
                 text_fallback=None, **kwargs):
        super(CheckboxCol, self).__init__(
            name,
            attr=attr,
            attr_list=attr_list,
            **kwargs)

        self.text_fallback = text_fallback

    def get_attr_list(self, attr):
        return super(CheckboxCol, self).get_attr_list(None)

    def text(self, item, attr_list):
        if attr_list:
            return self.from_attr_list(item, attr_list)
        elif self.text_fallback:
            return self.text_fallback
        else:
            return self.name

    def td_contents(self, item, attr_list):
        text = self.td_format(self.text(item, attr_list))
        attrs = dict(type='checkbox',name='table-checkbox',id='id_'+text)
        attrs.update({'class': 'custom-control-input'})
        Input = html.element('input', attrs=attrs, content=' ', escape_content=False)
        Label = html.element('label', attrs={'class':"custom-control-label", 'for':'id_'+text}, content='', escape_content=False)
        return html.element('div', attrs={'class':"custom-control custom-checkbox"}, content=Input+Label, escape_content=False)

### Custom campaign column class 
class CampaignCol(CheckboxCol):
    def td_contents(self, item, attr_list):
        text = self.td_format(self.text(item, attr_list))
        if item['campaign_timestamp']:
            href = 'relvals?cmssw_release={cmssw_release}&batch_name={batch_name}&campaign_timestamp={campaign_timestamp}'.format(
                    cmssw_release = item['cmssw_release'],
                    batch_name = item['batch_name'],
                    campaign_timestamp = item['campaign_timestamp']
                    )
            content = item['cmssw_release'] + '__' + item['batch_name'] + '-' + str(item['campaign_timestamp'])
            timestamp = '<small> ({})</small> '.format(datetime.fromtimestamp(item['campaign_timestamp']).strftime('%Y-%m-%d %H:%M:%S'))
            attrs = dict(href=href, name='campaign', id='campid_'+text, title='Show relvals having this Campaign ID')
            return html.element('a', attrs=attrs, content=content, escape_content=False)+timestamp
        else:
            return "Not set"

class RelvalTable(Table):
    checkbox = CheckboxCol('Checkbox', attr_list = ['prepid'], 
                            text_fallback='', 
                            td_html_attrs={'title': 'Show this relval'},
                            )
    prepid = LinkCol('Prep ID', endpoint='relvals.get_relval', 
                    url_kwargs=dict(prepid='prepid'), 
                    anchor_attrs={'title': 'Show this relval'}, attr='prepid',
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    status = Col('Status')

    _id = ActionCol("Actions", attr_list = ['prepid'], td_html_attrs={'style': 'white-space: nowrap'})

    cmssw_release = LinkCol('CMSSW Release', endpoint='relvals.get_relval', 
                    url_kwargs=dict(cmssw_release='cmssw_release'), 
                    anchor_attrs={'title':'Show relvals having this CMSSW release'}, 
                    attr='cmssw_release')

    jira_ticket = LinkCol('Jira', endpoint='relvals.get_relval', 
                    url_kwargs=dict(jira_ticket='jira_ticket'), 
                    anchor_attrs={'title': 'Show relvals having this Jira ticket'}, 
                    attr='jira_ticket', 
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    batch_name = LinkCol('Batch Name', endpoint='relvals.get_relval', 
                    url_kwargs=dict(batch_name='batch_name'), 
                    anchor_attrs={'title': 'Show relvals having this batch name'}, 
                    attr='batch_name'
                )

    campaign = CampaignCol('Campaign', attr_list = ['prepid'],
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    cpu_cores = Col('CPU Cores')

    label = Col('Label')

    memory = Col('Memory')

    workflow_id = Col('Workflow', td_html_attrs={'style': 'white-space: nowrap'})

    allow_sort = False
    table_id = 'relvals_list'
    allow_empty = True

    #Atrributes
    html_attrs = {"style":"margin-left: 0px; width: 100%;"}
    thead_attrs = {'style': 'white-space: nowrap'}

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction =  'desc'
        else:
            direction = 'asc'
        return url_for('relvals.relvals', sort=col_key, direction=direction)

    def get_tr_attrs(self, item):
        return {'id': item['prepid']}

    def th_contents(self, col_key, col):
        """Set checkbox to header to select all checkboxes"""
        if col_key == 'checkbox':
            attrs = dict(type='checkbox', name = "select-all", id='select-all-id')
            attrs.update({'class': 'custom-control-input'})
            Input = html.element('input', attrs=attrs, content=' ', escape_content=False)
            Label = html.element('label', attrs={'class':"custom-control-label", 'for':'select-all-id'}, content='', escape_content=False)
            return html.element('div', attrs={'class':"custom-control custom-checkbox"}, content=Input+Label, escape_content=False)
        return super(RelvalTable, self).th_contents(col_key, col)