from flask_wtf import FlaskForm
from resources.wtforms_form import Form as CustomForm
from wtforms import SubmitField, FormField, Form
from wtforms.validators import DataRequired, StopValidation, NumberRange
from markupsafe import Markup
from wtforms.widgets.core import html_params
from resources.custom_form_fields import (ButtonField,
                                          CustomSelect,
                                          SBooleanField,
                                          SFieldList,
                                          SFloatField,
                                          SIntegerField,
                                          SRadioField,
                                          SSelectField,
                                          SStringField,
                                          STextAreaField
                                         )

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

class SFormField(FormField):
    widget = TableWidget()

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

    size_per_event  = SStringField('Size Per Event',
                    render_kw = classDict | {"placeholder":"Size per event"},
                    label_rkw = label_kw
                    )
    time_per_event  = SStringField('Time Per Event',
                    render_kw = classDict | {"placeholder":"Time per event"},
                    label_rkw = label_kw
                    )

    events_per_lumi = SStringField('Events per lumi',
                        render_kw = classDict,
                        label_rkw = label_kw
                        )
    lumis_per_job = SStringField('Lumis per job',
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
    hlt_menu = SStringField('HLT menu',
                        render_kw = {'class': 'form-control form-control-sm',
                                    "placeholder":"Custom HLT menu, if empty default GRun menu of the release is used"
                                    },
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