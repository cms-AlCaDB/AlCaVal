from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList
from wtforms.validators import DataRequired


class TicketForm(FlaskForm):
    batch_name = StringField('Batch Name', validators=[DataRequired()])
    cmssw_release = StringField('CMSSW Release', validators=[DataRequired()])
    label = StringField('Label (--label)')
    hlt_gt = StringField('HLT Global Tag')
    prompt_gt = StringField('Prompt Global Tag')
    express_gt = StringField('Express Global Tag')
    workflow_ids = StringField('Workflow IDs', validators=[DataRequired()])
    submit = SubmitField('Submit')