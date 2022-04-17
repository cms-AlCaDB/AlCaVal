from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList, TextAreaField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea


class TicketForm(FlaskForm):
    prepid = StringField('Prep ID')
    batch_name = StringField('Batch Name', validators=[DataRequired()])
    cmssw_release = StringField('CMSSW Release', validators=[DataRequired()])
    label = StringField('Label (--label)')
    hlt_gt = StringField('HLT Global Tag')
    prompt_gt = StringField('Prompt Global Tag')
    express_gt = StringField('Express Global Tag')
    notes = TextAreaField('Notes',  render_kw={"rows": 10, 
                          'placeholder': "Notes: e.g. Description of the request. Twiki reference or Jira ticket ID"})
    workflow_ids = StringField('Workflow IDs', validators=[DataRequired()])
    submit = SubmitField('Submit')