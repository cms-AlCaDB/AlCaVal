from datetime import datetime
from flask import url_for, Markup
from flask_table import Table, Col, LinkCol, html
from core_lib.utils.global_config import Config
from flask import session

class ActionCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)

    def td_format(self, content, item):
        status_list = ['new', 'approving', 'approved', 'submitting', 'submitted', 'done', 'archived', 'nothing']
        newtab = 'target="_blank" rel="noopener noreferrer"'
        divAction = "<div class='actions'>{mylinks}</div>"
        isAdmin = bool(session.get('user').get('response').get('role_index') >= 2)
        isManager = bool(session.get('user').get('response').get('role_index') >= 1)

        edit = f"<a class='cls_edit_relval' href='/relvals/edit?prepid={content}' title='Edit this relval'>Edit</a>"
        edit = edit if isManager else ""
        clone = f"<a class='cls_clone_relval' href='/relvals/edit?clone={content}' title='Clone this relval'>Clone</a>"
        clone = clone if isManager else ""
        cmsDriver = f"<a href='api/relvals/get_cmsdriver/{content}' title='Show cmsDriver.py commands for this relval'>cmsDriver</a>"
        job_dict = f"<a href='api/relvals/get_dict/{content}' title='Show job dict of ReqMgr2 workflow'>Job dict</a>"

        title = "title='Check the status of the submision'"
        stats2 = f"<a href='https://cms-pdmv.cern.ch/stats/?prepid={content}' {newtab} {title}>Stats2</a>"
        stats2 = stats2 if status_list.index(item['status']) > 3 else ""

        prev_status = f"""<a id="prev_status_{content}" onclick="prevStatus(['{content}'])" href="javascript:void(0);" title='Move Relval to previous status'>Previous</a>"""
        prev_status = prev_status if (item['status'] != 'new' and isManager) else ""

        new_status = status_list[status_list.index(item['status'])+1]
        next_status = f"""<a class="cls_next_status nextStatus_{content}" onclick="nextStatus(['{content}'])" href="javascript:void(0);" title='Move Relval to next status: from "{item['status']}" to "{new_status}"'>Next</a>"""
        next_status = next_status if (item['status'] != 'done' and isManager) else ""

        update_workflows = f"""<a id="updateWorkflows_{content}" onclick="updateWorkflows(['{content}'])" href="javascript:void(0);" title='Update RelVal information from ReqMgr2'>Update Workflows</a>"""
        update_workflows = update_workflows if (item['status'] == 'submitted' and isAdmin) else ""

        ticket = f"<a href='tickets?created_relvals={content}' title='Show a ticket from which this relval was created'>Ticket</a>"

        delete = f"""<a class="delete_relval delete_{content}" onclick="delete_relval(['{content}'])" href="javascript:void(0);" title='Delete relval'>Delete</a>"""
        delete = delete if (item['status'] == 'new' and isManager) else ""
        
        links = "".join([edit, clone, delete, cmsDriver, job_dict, stats2, ticket, prev_status, next_status, update_workflows])
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

### Request manager status column class 
class ReqMgr2Col(CheckboxCol):
    def td_contents(self, item, attr_list):
        text = self.td_format(self.text(item, attr_list))
        if len(item['workflows']):
            name = item['workflows'][-1]['name']
            status = item['workflows'][-1].get('status_history')
            status = None if not status else status[-1].get('status')
            time = item['workflows'][-1].get('status_history')
            time = 1 if not status else time[-1].get('time')
            href = f'{Config.get("cmsweb_url")}/reqmgr2/fetch?rid=request-{name}'
            time = '<small> ({})</small> '.format(datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S'))
            attrs = dict(href=href, name='reqmgr2status', id='reqmgr2status_'+text, title='Status of submitted relval')
            return html.element('a', attrs=attrs, content=status, escape_content=False)+time
        else:
            return "Not submitted"

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

    jira_ticket = LinkCol('Jira', endpoint='relvals.get_relval', 
                    url_kwargs=dict(jira_ticket='jira_ticket'), 
                    anchor_attrs={'title': 'Show relvals having this Jira ticket'}, 
                    attr='jira_ticket', 
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    reqmgr_status = ReqMgr2Col(
                        'ReqMgr2 Status',
                        attr_list = ['prepid'],
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

    cmssw_release = LinkCol('CMSSW Release', endpoint='relvals.get_relval', 
                    url_kwargs=dict(cmssw_release='cmssw_release'), 
                    anchor_attrs={'title':'Show relvals having this CMSSW release'}, 
                    attr='cmssw_release')

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