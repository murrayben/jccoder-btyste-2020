# Import request
from flask import request

# Import the base form class and recaptcha
from flask_wtf import FlaskForm

# Import all the necessary fields such as a textarea (TextAreaField()).
from wtforms import BooleanField, SelectMultipleField, StringField, SubmitField, TextAreaField

# Import all the validators such as making sure that there is something inside of a field (DataRequired())
from wtforms.validators import DataRequired, Length

# Import Tag model to loop through all the Tags (multiple select)
from ..models import Tag

class AnnouncementForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(1, 64, message="Title should be no more than 64 characters.")])
    body = TextAreaField("Content", validators=[DataRequired()])
    summary = TextAreaField("Summary", validators=[DataRequired()])
    tags = SelectMultipleField("Tags", coerce=int)
    published = BooleanField("Do you want to make this public?")
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(AnnouncementForm, self).__init__(*args, **kwargs)
        self.tags.choices = [(tag.id, tag.name) for tag in Tag.query.order_by(Tag.name.asc()).all()]

class SearchForm(FlaskForm):
    q = StringField('Search query...', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)