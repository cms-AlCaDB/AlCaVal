from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList, TextAreaField
from wtforms.validators import DataRequired, InputRequired, ValidationError, StopValidation, Length
from wtforms.widgets import TextArea

from markupsafe import Markup
from wtforms.widgets.core import html_params
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
        if not (field.data and (not isinstance(field.data, str) or field.data.strip())) and hltgt:
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)

def validate_jira_ticket(form, field):
    print(form.data, "FOMR DATA")
    if form.data['hlt_gt'].strip() == '':
        message = field.gettext('This field is required.')
        raise StopValidation(message)

class TicketForm(FlaskForm):
    prepid = StringField('Prep ID')
    batch_name = StringField('Batch Name', validators=[DataRequired()])
    cmssw_release = StringField('CMSSW Release', validators=[DataRequired()])
    jira_ticket = SelectField('Jira Ticket', choices=[["", "Select Jira ticket to associated with this"], ["None", "Create New Ticket"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default=''
                               )
    label = StringField('Label (--label)')

    matrix_choices = [
        ['alca', 'alca'], ['standard', 'standard'], ['upgrade', 'upgrade'], 
        ['generator', 'generator'], ['pileup', 'pileup'], ['premix', 'premix'],
        ['extendedgen', 'extendedgen'], ['gpu', 'gpu']
    ]
    matrix = SelectField('Matrix (--what)', choices=matrix_choices,
                           validators=[InputRequired()],
                           default='alca'
                        )
    hlt_gt = StringField('HLT Global Tag', validators=[Length(min=5, max=100)])
    prompt_gt = StringField('Prompt Global Tag')
    express_gt = StringField('Express Global Tag')
    common_prompt_gt = StringField('Common Prompt GT',
                        validators=[GTDataRequired(message="Since you have chosen to use HLT global tag, you are required to provide common prompt global tag, which is to be used in RECO step of workflow")],
                        render_kw={'placeholder': 'Global tag to be used in RECO step of HLT workflow'}
                        )
    notes = TextAreaField('Notes',  render_kw={"rows": 10, 
                          'placeholder': "Notes: e.g. Description of the request. "})
    workflow_ids = StringField('Workflow IDs', validators=[DataRequired()])
    submit = SubmitField('Submit')