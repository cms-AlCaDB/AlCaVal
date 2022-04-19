from flask import url_for, Markup
from flask_table import Table, Col, LinkCol, html

class ActionCol(Col):
    def td_contents(self, item, attr_list):
        return self.td_format(self.from_attr_list(item, attr_list), item)

    def td_format(self, content, item):
        divAction = "<div class='actions'>{mylinks}</div>"
        edit = f"<a href='/relvals/edit?prepid={content}'>Edit</a>"
        clone = f"<a href='/relvals/edit?clone={content}'>Clone</a>"
        cmsDriver = f"<a href='api/relvals/get_cmsdriver/{content}'>cmsDriver</a>"
        job_dict = f"<a href='api/relvals/get_dict/{content}' title='Show job dict of ReqMgr2'>Job dict</a>"
        ticket = f"<a href='tickets?created_relvals={content}'>Ticket</a>"
        if item['status'] == 'new':
            delete = f"""<a class="delete_relval delete_{content}" onclick="delete_relval('{content}')" href="javascript:void(0);">Delete</a> """
            links = "".join([edit, clone, delete, cmsDriver, job_dict, ticket])
            return divAction.format(mylinks=links)
        else:
            links = "".join([edit, clone, cmsDriver, job_dict, ticket])
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
        attrs = dict(type='checkbox',name='table-checkbox', id='id_'+text)
        return html.element('input', attrs=attrs, content=' ', escape_content=False)

class RelvalTable(Table):
    checkbox = CheckboxCol('Checkbox',attr_list = ['prepid'],text_fallback='', 
                            td_html_attrs={'style': "padding-left: 18px;"},
                            )
    prepid = LinkCol('Prep ID', endpoint='relvals.get_relval', 
                    url_kwargs=dict(prepid='prepid'), 
                    anchor_attrs={'class': 'myclass'}, attr='prepid',
                    td_html_attrs={'style': 'white-space: nowrap'}
                    )

    status = Col('Status')

    _id = ActionCol("Actions", td_html_attrs={'style': 'white-space: nowrap'})

    cmssw_release = LinkCol('CMSSW Release', endpoint='relvals.get_relval', 
                    url_kwargs=dict(cmssw_release='cmssw_release'), 
                    anchor_attrs={}, attr='cmssw_release')

    batch_name = LinkCol('Batch Name', endpoint='relvals.get_relval', 
                    url_kwargs=dict(batch_name='batch_name'), 
                    anchor_attrs={}, 
                    attr='batch_name'
                )

    cpu_cores = Col('CPU Cores')

    label = Col('Label')

    memory = Col('Memory')

    workflow_id = Col('Workflow', td_html_attrs={'style': 'white-space: nowrap'})

    allow_sort = False
    table_id = 'relvals_list'
    allow_empty = True

    #Header Atrributes
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
        attrs = dict(type='checkbox', name = "select-all", id='select-all-id')
        if col_key == 'checkbox':
            return html.element('input', attrs=attrs, content=' ', escape_content=False)
        return super(RelvalTable, self).th_contents(col_key, col)