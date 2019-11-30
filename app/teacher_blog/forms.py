from flask import redirect, request, session, url_for
from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, RadioField,
                     SelectMultipleField, StringField, SubmitField,
                     TextAreaField, ValidationError)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from ..models import Chapter, PostCategory, User, db

class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(1, 64, message="Title should be no more than 64 characters.")])
    body = TextAreaField("Content", validators=[DataRequired()])
    categories = SelectMultipleField("Categories (You can hold down Ctrl or Command to select more than one)", coerce=int)
    published = BooleanField("Do you want to make this public?")
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.categories.choices = [(category.id, category.name) for category in PostCategory.query.filter(db.not_(Chapter.query.filter(Chapter.title == PostCategory.name).exists())).order_by(PostCategory.name.asc()).all()]

class CommentForm(FlaskForm):
    body = TextAreaField("Content *", validators=[DataRequired()])
    submit = SubmitField("Save")

class SearchForm(FlaskForm):
    q = StringField("Press Enter to search...", validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)
