# Modified WTForm classes and Widgets
from wtforms import (SelectField,
                    StringField,
                    FieldList,
                    SelectMultipleField,
                    TextAreaField,
                    RadioField,
                    BooleanField,
                    IntegerField,
                    FloatField
                    )
import wtforms.widgets as widgets

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

class ListWidget:
    """
    Default widget modified for putting id to the list tag
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
            kwargs['onclick'] = "addSet()"

        return Markup('<button {params}>{label}</button>'.format(
            params=self.html_params(name=field.name, **kwargs),
            label=field.label.text)
        )

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

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
                label if label is not None else name.replace("_", " ").title(),
                label_rkw=label_rkw)

class SStringField(StringField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(**kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class ButtonField(StringField):
    widget = ButtonWidget()
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(**kw)
        self.label = SetLabel(self.id, label, '', label_rkw)

class SSelectField(SelectField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SFieldList(FieldList):
    widget = ListWidget()
    def __init__(self, unbound_field, separator=" ", last_index=0, **kwargs):
        super().__init__(unbound_field, separator=separator, **kwargs)
        self.last_index = last_index

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

class SIntegerField(IntegerField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SFloatField(FloatField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)
