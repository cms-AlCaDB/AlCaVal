from flask_wtf import FlaskForm, Form
from wtforms import FormField, SubmitField

from wtforms.validators import DataRequired, InputRequired
from resources.custom_form_fields import ButtonField, CustomSelect, SFieldList, SSelectField

label_kw   = {'class': 'col-form-label-sm', 'style': 'font-weight: normal; margin-bottom: 0px;'}
classDict   = {'class': 'form-control form-control-sm'}
class datasetForm(Form):
    tar_relval = SSelectField('Target Relval', choices=[["", "Select one of the following relvals"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default='',
                                render_kw = classDict,
                                label_rkw = label_kw
                               )
    ref_relval = SSelectField('Reference Relval', choices=[["", "Select one of the following relvals"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default='',
                                render_kw = classDict,
                                label_rkw = label_kw
                               )
    delete_set = ButtonField('Delete Set',
                    render_kw={'class': 'btn btn-sm btn-danger', 
                                'onclick': 'delete_set(this.id)'
                                }, 
                    label_rkw = label_kw
                    )

class ComparisonForm(FlaskForm):
    jira_ticket = SSelectField('Jira Ticket', choices=[["", "Select Jira ticket to choose DQM dataset from"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default='',
                                render_kw = classDict,
                                label_rkw = label_kw
                               )
    Set  = SFieldList(FormField(datasetForm), 
                        label='Set', 
                        min_entries=0, 
                        max_entries=50,
                        render_kw = {'style': 'padding-left:0px; width: 100%'}
                        )
    # search = SearchField('Search Here', 
    #                     render_kw = classDict,
    #                     )
    submit = SubmitField('Compare DQM plots')

class SetForm(Form):
    Set = SFieldList(FormField(datasetForm), 
                    label='Set', 
                    min_entries=0, 
                    max_entries=50,
                    render_kw = {'style': 'padding-left:0px; width: 100%'}
                    )