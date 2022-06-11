from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList, TextAreaField, IntegerField
from wtforms.validators import DataRequired, InputRequired, ValidationError, StopValidation, Length, NumberRange
from wtforms.widgets import TextArea
from wtforms import widgets

from markupsafe import Markup
from wtforms.widgets.core import html_params
from wtforms.fields.core import Label as BaseLabel

class CustomSelect:
    """
    Borrowed from: https://stackoverflow.com/questions/44379016/disabling-one-of-the-options-in-wtforms-selectfield/61762617
    """

    def __init__(self, multiple=False):
        self.multiple = multiple

    def __call__(self, field, option_attr=None, **kwargs):
        if option_attr is None:
            option_attr = {}
        kwargs.setdefault("id", field.id)
        if self.multiple:
            kwargs["multiple"] = True
        if "required" not in kwargs and "required" in getattr(field, "flags", []):
            kwargs["required"] = True
        html = ["<select %s>" % html_params(name=field.name, **kwargs)]
        for option in field:
            attr = option_attr.get(option.id, {})
            html.append(option(**attr))
        html.append("</select>")
        return Markup("".join(html))

class GTDataRequired(object):
    """Validator for Common Prompt GT
    """
    def __init__(self, message=None):
        self.message = message
        self.field_flags = {}

    def __call__(self, form, field):
        hltgt = bool(form.data['hlt_gt'].strip()=='')
        if field.data and (not isinstance(field.data, str) or field.data.strip()) and not hltgt:
            return
        if hltgt:
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)

class Label(BaseLabel):
    """
    An HTML form label.
    """
    def __init__(self, field_id, text, label_rkw={}):
        super().__init__(field_id, text)
        self.label_rkw = label_rkw

    def __call__(self, text=None, **kwargs):
        kwargs.update(**self.label_rkw)
        return super().__call__(text=None, **kwargs)

def SetLabel(myid, label, name, label_rkw):
    return Label(myid,
                label if label is not None else self.gettext(name.replace("_", " ").title()),
                label_rkw=label_rkw)

class SSelectField(SelectField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SStringField(StringField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class STextAreaField(TextAreaField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SIntegerField(IntegerField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class TicketForm(FlaskForm):
    label_rkw = {'class': 'col-form-label-sm'}
    classDict = {'class': 'form-control form-control-sm'}
    prepid = SStringField(
                render_kw=classDict | {'disabled':''},
                label="My Prep ID",
                label_rkw = label_rkw
                )
    batch_name = SStringField('Batch Name',
                validators=[DataRequired(message="Please provide appropreate batch name")],
                render_kw = classDict | {"placeholder":"Appropriate batch name"},
                label_rkw = {'class': 'col-form-label-sm required'}
                )
    cmssw_release = SStringField('CMSSW Release',
                validators=[DataRequired(message="Please provide correct CMSSW release")],
                render_kw = classDict | {"placeholder":"E.g CMSSW_12_3_..."},
                label_rkw = {'class': 'col-form-label-sm required'}
                )
    jira_ticket = SSelectField('Jira Ticket', 
                choices=[["", "Select Jira ticket to associated with this"], ["None", "Select nothing for a moment"]],
                validators=[DataRequired(message="Please select Jira ticket out of given list. Or choose to create new")],
                widget=CustomSelect(),
                default='',
                render_kw = classDict | {'option_attr': {"jira_ticket-0": {"disabled": True, "hidden": True}} },
                label_rkw = label_rkw
                )
    label = SStringField('Label (--label)',
                render_kw = classDict | {'placeholder': 'This label will be included in ReqMgr2 workflow name'},
                label_rkw = label_rkw
                )

    # command = SStringField('Command (--command)',
    #             render_kw = classDict | {"placeholder":"Arguments that will be added to all cmsDriver commands"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    # command_steps = SStringField('Command Steps',
    #             render_kw = classDict | {"placeholder":"E.g. RAW2DIGI, L1Reco, RECO, DQM"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    cpu_cores = SIntegerField('CPU Cores (-t)', default=8, validators=[NumberRange(min=1, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )

    memory = SIntegerField('Memory', default=16000, validators=[NumberRange(min=0, max=30000)],
                render_kw = classDict | {'step': 1000},
                label_rkw = {'class': 'col-form-label-sm'}
                )
    n_streams = SIntegerField('Streams (--nStreams)', default=2, validators=[NumberRange(min=0, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )
    matrix_choices = [
        ['alca', 'alca'], ['standard', 'standard'], ['upgrade', 'upgrade'], 
        ['generator', 'generator'], ['pileup', 'pileup'], ['premix', 'premix'],
        ['extendedgen', 'extendedgen'], ['gpu', 'gpu']
    ]
    matrix = SSelectField('Matrix (--what)', choices=matrix_choices,
                           validators=[DataRequired()],
                           default='alca',
                           render_kw = classDict,
                           label_rkw = label_rkw
                        )

    hlt_gt = SStringField('HLT Global Tag',
                validators=[],
                render_kw = classDict | {"id":"hlt_gt", "placeholder":"HLT Global Tag. Target or Reference"},
                label_rkw = label_rkw
                )
    common_prompt_gt = SStringField('Common Prompt GT',
                        validators=[GTDataRequired(message="Since you have chosen to use HLT global tag, you are required to provide common prompt global tag, which is to be used in RECO step of workflow")],
                        render_kw= classDict | {'placeholder': 'Global tag to be used in RECO step of HLT workflow'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    prompt_gt = SStringField('Prompt Global Tag',
                render_kw = classDict | {'placeholder': 'Prompt Global Tag. Target or Reference'},
                label_rkw = label_rkw
                )
    express_gt = SStringField('Express Global Tag',
                render_kw = classDict | {'placeholder': 'Express Global Tag. Target or Reference'},
                label_rkw = label_rkw
                )
    workflow_ids = SStringField('Workflow IDs', validators=[DataRequired()],
                        render_kw = classDict | {'placeholder': 'Workflow IDs separated by comma. E.g. 1.1,1.2'},
                        label_rkw = {'class': 'col-form-label-sm required'}
                        )
    notes = STextAreaField('Notes',  
                          render_kw = classDict | {"rows": 5, 'style': 'padding-bottom: 5px;',
                          'placeholder': "Description of the request. TWiki links etc.."},
                          label_rkw = label_rkw
                          )
    submit = SubmitField('Submit')