from flask_wtf import FlaskForm
from resources.wtforms_form import Form as CustomForm
from wtforms import (SubmitField,
                        SelectField,
                        StringField,
                        FormField,
                        Form,
                        FieldList,
                        TextAreaField,
                        BooleanField,
                        RadioField,
                        IntegerField,
                        FloatField
                    )
from wtforms.validators import (DataRequired,
                                InputRequired,
                                ValidationError,
                                StopValidation,
                                Length,
                                NumberRange
                                )
from wtforms.widgets import TextArea
from wtforms import widgets

from markupsafe import Markup
from wtforms.widgets.core import html_params
from wtforms.fields.core import Label as BaseLabel

class TableWidget:
    """
    Custom TableWidget for FormField
    """

    def __init__(self, with_table_tag=True):
        self.with_table_tag = with_table_tag

    def __call__(self, field, **kwargs):
        html = []
        if self.with_table_tag:
            kwargs.setdefault("id", field.id)
            html.append("<table %s>" % html_params(**kwargs))
        hidden = ""
        for subfield in field:
            index = subfield.id.split('step ')[1].split('-')[0]
            if subfield.type in ("HiddenField", "CSRFTokenField"):
                hidden += str(subfield)
            elif (subfield.label.text in ['Driver', 'Delete Step', 'Input']):
                html.append(
                    "<tr class='%s-row'><td colspan='2'>%s%s</td></tr>"
                    % (subfield.name.replace(' ', '_'), hidden, str(subfield).replace('Delete Step', "DELETE STEP "+index))
                )
                hidden = ""
            elif 'step_type' in subfield.name:
                is_hidden = "hidden" if index !='1' else ""
                html.append(
                    "<tr %s><td class='first-column'>%s</td><td>%s%s</td></tr>"
                    % (is_hidden, str(subfield.label), hidden, str(subfield))
                )
                hidden = ""                
            else:
                if subfield.name.split('-')[1] in ['keep_output', 'events_per_lumi']:
                    className = 'class="step_'+index+'-driver-row"'
                elif subfield.name.split('-')[1] in ['driver']:
                    if subfield.name.split('-')[2] in ['fast']:
                        className = 'id="step '+index+'-driver-fast-row" hidden'
                    else:
                        className = ''
                else:
                    className = ''
                html.append(
                    "<tr %s><td class='first-column'>%s</td><td class='second-column'>%s%s</td></tr>"
                    % (className, str(subfield.label), hidden, str(subfield))
                )
                hidden = ""
        if self.with_table_tag:
            html.append("</table>")
        if hidden:
            html.append(hidden)
        return Markup("".join(html))

class ButtonWidget(object):
    """
    Renders a multi-line text area.
    `rows` and `cols` ought to be passed as keyword args when rendering.
    """
    input_type = 'button'

    html_params = staticmethod(html_params)

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.input_type)
        if 'value' not in kwargs:
            kwargs['value'] = field._value()
        if 'onclick' not in kwargs:
            kwargs['onclick'] = "addStep()"

        return Markup('<button {params}>{label}</button>'.format(
            params=self.html_params(name=field.name, **kwargs),
            label=field.label.text)
        )

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

class ListWidget:
    """Default widget modified for putting id to the list tag
    """
    def __init__(self, html_tag="ul", prefix_label=True):
        assert html_tag in ("ol", "ul")
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = [f"<{self.html_tag} {html_params(**kwargs)}>"]
        for subfield in field:
            if self.prefix_label:
                cstyle = "style='list-style: none; padding-top:10px; padding-bottom:10px;border-bottom: 1px solid grey;'"
                html.append(f"<li id='{subfield.label.field_id}_listid' {cstyle}>{subfield.label(style='font-weight: bold;')} {subfield()}</li>")
            else:
                # executed for SRadioField
                if 'step_type' in subfield.name:
                    func = "toggleDriverOption(this.id)"
                if 'data_mc' in subfield.name:
                    func = "toggleDataMCFast(this.id)"
                radiobtnStyle = "style='display: inline-list-item; list-style: none;padding-right: 10px;'"
                html.append(f"<li {radiobtnStyle}>{subfield(onclick=func)} {subfield.label}</li>")
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))

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
        super().__init__(**kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class STextAreaField(TextAreaField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SRadioField(RadioField):
    widget = ListWidget(prefix_label=False)
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SBooleanField(BooleanField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class ButtonField(StringField):
    widget = ButtonWidget()
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(**kw)
        self.label = SetLabel(self.id, label, '', label_rkw)

class SFieldList(FieldList):
    widget = ListWidget()
    def __init__(self, unbound_field, separator=" ", last_index=0, **kwargs):
        super().__init__(unbound_field, separator=separator, **kwargs)
        self.last_index = last_index

class SFormField(FormField):
    widget = TableWidget()

class SIntegerField(IntegerField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SFloatField(FloatField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class InputDataStepForm(Form):
    label_kw   = {'class': 'col-form-label-sm', 'style': 'font-weight: normal; margin-bottom: 0px;'}
    classDict   = {'class': 'form-control form-control-sm'}
    dataset     = SStringField('Dataset',
                    render_kw = classDict,
                    label_rkw = label_kw
                    )
    lumisection = STextAreaField('Lumisection ranges',
                    render_kw = classDict | {"rows": 10, 
                                'onkeyup': 'validateJSON(this.id)'
                                },
                    label_rkw = label_kw
                    )
    run         = STextAreaField('Runs',
                    render_kw = classDict | {"rows": 5, 
                                'onkeyup': 'validateRunNumbers(this.id)',
                                'placeholder': 'Run number seperated by comma'
                                },
                    label_rkw = label_kw
                    )
    label       = SStringField('Label',
                    render_kw = classDict,
                    label_rkw = label_kw
                    )

class DriverOptionsForm(CustomForm):
    label_kw   = {'class': 'col-form-label-sm', 'style': 'font-weight: normal; margin-bottom: 0px;'}
    classDict = {'class': 'form-control form-control-sm'}
    scenario_choices = [['', ''],
                        ['pp', 'pp'],
                        ['cosmics','cosmics'],
                        ['nocoll', 'nocoll'],
                        ['HeavyIons', 'HeavyIons']
                    ]
    beamspot = SStringField('--beamspot',
                render_kw = classDict,
                label_rkw = label_kw
                )
    conditions = SStringField('--conditions',
                render_kw = classDict,
                label_rkw = label_kw
                )
    customise = SStringField('--customise',
                render_kw = classDict,
                label_rkw = label_kw
                )
    customise_commands = SStringField('--customise_commands',
                render_kw = classDict,
                label_rkw = label_kw
                )
    datatier = SStringField('--datatier',
                render_kw = classDict,
                label_rkw = label_kw
                )
    era     = SStringField('--era', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    eventcontent = SStringField('--eventcontent', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    filetype = SStringField('--filetype', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    geometry = SStringField('--geometry', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    hltProcess = SStringField('--hltProcess', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    nStreams = SStringField('--nStreams', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    pileup = SStringField('--pileup', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    pileup_input = SStringField('--pileup_input', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    process = SStringField('--process',
                        render_kw = classDict, label_rkw = label_kw
                        )
    relval = SStringField('--relval', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    runUnscheduled = SBooleanField('--runUnscheduled',
                        render_kw = {'class': ''},
                        label_rkw = label_kw
                        )
    scenario      = SSelectField('--scenario',
                        choices=scenario_choices,
                        default='alca',
                        render_kw = classDict,
                        label_rkw = label_kw
                        )
    step        = SStringField('--step', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    data_mc     = SRadioField('Data, MC', 
                    choices=[('data','--data'),('mc','--mc')],
                    label_rkw = label_kw,
                    render_kw = {'style': 'padding-left:0px; display:inline-flex;'},
                    default='data'
                    )
    fast        = SBooleanField('--fast',
                    render_kw = {'class': ''},
                    label_rkw = label_kw
                    )
    fragment_name = SStringField('Fragment name', 
                        render_kw = classDict, label_rkw = label_kw
                        )
    extra = SStringField('Extra', 
                        render_kw = classDict, label_rkw = label_kw
                        )
class cmsDriverStepForm(Form):
    label_kw   = {'class': 'col-form-label-sm', 'style': 'font-weight: normal; margin-bottom: 0px;'}
    classDict   = {'class': 'form-control form-control-sm'}
    name        = SStringField(label='Name',
                    validators = [DataRequired(message="Please provide appropreate name for the step")],
                    render_kw = classDict,
                    label_rkw = label_kw | {'class': 'col-form-label-sm required'}
                    )

    cmssw_release = SStringField('CMSSW Release',
                    render_kw = classDict | {"placeholder":"E.g CMSSW_12_3_..."},
                    label_rkw = label_kw
                    )

    scram_arch  = SStringField('SCRAM Arch',
                    render_kw = classDict | {"placeholder":"If empty, uses default value of the release"},
                    label_rkw = label_kw
                    )

    events_per_lumi = SStringField('Events per lumi',
                        render_kw = classDict,
                        label_rkw = label_kw
                        )
    keep_output = SBooleanField('Keep Output',
                    render_kw = {'class': ''},
                    label_rkw = label_kw
                    )
    step_type   = SRadioField('Relval Step Type', 
                    choices=[('input','Input Datataset'),('driver','cmsDriver')],
                    label_rkw = label_kw,
                    render_kw = {'style': 'padding-left:0px; display:inline-flex;'},
                    default='driver'
                    )
    input       = SFormField(InputDataStepForm)
    driver      = SFormField(DriverOptionsForm)
    delete_step = ButtonField('Delete Step',
                    render_kw={'class': 'btn btn-sm btn-danger', 
                                'onclick': 'delete_step(this.id)'
                                }, 
                    label_rkw = label_kw
                    )

class RelvalForm(FlaskForm):
    matrix_choices  = [
                    ['alca', 'alca'], ['standard', 'standard'], ['upgrade', 'upgrade'], 
                    ['generator', 'generator'], ['pileup', 'pileup'], ['premix', 'premix'],
                    ['extendedgen', 'extendedgen'], ['gpu', 'gpu']
                    ]

    prepid      = SStringField('Prep ID',
                    render_kw={'class': 'form-control form-control-sm', 'disabled':''},
                    label_rkw = {'class': 'col-form-label-sm'}
                    )
    batch_name  = SStringField('Batch Name',
                    validators=[DataRequired(message="Please provide appropreate batch name")],
                    render_kw = {'class': 'form-control form-control-sm', "placeholder":"Appropriate batch name"},
                    label_rkw = {'class': 'col-form-label-sm required'}
                    )
    cmssw_release = SStringField('CMSSW Release',
                    validators=[DataRequired(message="Please provide correct CMSSW release")],
                    render_kw = {'class': 'form-control form-control-sm', "placeholder":"E.g CMSSW_12_3_..."},
                    label_rkw = {'class': 'col-form-label-sm required'}
                    )
    jira_ticket = SSelectField('Jira Ticket', 
                    choices=[
                                ["", "Select Jira ticket to associated with this"], 
                                ["None", "Select nothing for a moment"]
                            ],
                    validators=[DataRequired(message="Please select Jira ticket out of given list. Or choose to create new")],
                    widget=CustomSelect(),
                    default='',
                    render_kw = {'class': 'form-control form-control-sm', 'option_attr': {"jira_ticket-0": {"disabled": "", "hidden": ""}}},
                    label_rkw = {'class': 'col-form-label-sm'}
                    )
    cpu_cores = SIntegerField('CPU Cores (-t)', default=8, validators=[NumberRange(min=1, max=16)],
                render_kw = {'class': 'form-control form-control-sm'},
                label_rkw = {'class': 'col-form-label-sm'}
                )

    memory = SIntegerField('Memory', default=16000, validators=[NumberRange(min=0, max=30000)],
                render_kw = {'class': 'form-control form-control-sm', 'step': 1000},
                label_rkw = {'class': 'col-form-label-sm'}
                )
    matrix      = SSelectField('Matrix (--what)', choices=matrix_choices,
                        validators=[DataRequired()],
                        default='alca',
                        render_kw = {'class': 'form-control form-control-sm'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    label       = SStringField('Label (--label)',
                        render_kw = {'class': 'form-control form-control-sm', 'placeholder': 'This label will be included in ReqMgr2 workflow name'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )

    fragment    = STextAreaField('Custom Fragment',  
                        render_kw = {
                                'class': 'form-control form-control-sm',
                                "rows": 10
                                },
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    notes       = STextAreaField('Notes',  
                        render_kw = {
                                'class': 'form-control form-control-sm',
                                "rows": 5,
                                'placeholder': "Description of the request. TWiki links etc.."
                                },
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    scram_arch  = SStringField('SCRAM Arch',
                        render_kw = {'class': 'form-control form-control-sm', "placeholder":"If empty, uses default value of the release"},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    step        = SFieldList(SFormField(cmsDriverStepForm), 
                        label='Steps', 
                        min_entries=0, 
                        max_entries=50,
                        render_kw = {'style': 'padding-left:0px; width: 100%'}
                        )
    workflow_id = SFloatField('Workflow ID', default=0, validators=[NumberRange(min=0, max=300000)],
                        render_kw = {'class': 'form-control form-control-sm', 'readonly': ''},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    workflow_name = SStringField('Workflow Name',
                        render_kw = {'class': 'form-control form-control-sm'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    size_per_event = SIntegerField('Size per event', default=1, validators=[NumberRange(min=1, max=300000)],
                        render_kw = {'class': 'form-control form-control-sm'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    time_per_event = SIntegerField('Time per event', default=1, validators=[NumberRange(min=1, max=300000)],
                        render_kw = {'class': 'form-control form-control-sm'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    submit = SubmitField('Submit')

class StepsForm(FlaskForm):
    step = SFieldList(SFormField(cmsDriverStepForm), 
                        label='Steps', 
                        min_entries=0, 
                        max_entries=50,
                        render_kw = {'style': 'padding-left:0px; width:100%'}
                        )