from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, InputRequired
import wtforms.widgets as widgets
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

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class ComparisonForm(FlaskForm):
    jira_ticket = SelectField('Jira Ticket', choices=[["", "Select Jira ticket to choose DQM dataset from"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default=''
                               )
    target_dataset = SelectField('Target Dataset', choices=[["", "Select one of the following dataset"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default=''
                               )
    # target_dataset = MultiCheckboxField('Target Dataset', coerce=int, choices=[["", "Select one of the following dataset"]])

    reference_dataset = SelectField('Reference Dataset', choices=[["", "Select one of the following dataset"]],
                               validators=[InputRequired()],
                               widget=CustomSelect(),
                               default=''
                               )
    submit = SubmitField('Compare DQM plots')