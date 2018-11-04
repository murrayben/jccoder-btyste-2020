from flask import request
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, HiddenField, StringField
from wtforms.validators import DataRequired

class NewPageQuestion(FlaskForm):
    text = TextAreaField('Question *', validators=[DataRequired()])
    submit_question = SubmitField('Submit Question')

class NewPageAnswer(FlaskForm):
    question_id = HiddenField('')
    answer = TextAreaField('Answer *', validators=[DataRequired()])
    submit_answer = SubmitField('Submit Answer')

class EditPageAnswer(FlaskForm):
    answer = TextAreaField('Answer *', validators=[DataRequired()])
    submit_answer = SubmitField('Edit Answer')

class SearchForm(FlaskForm):
    q = StringField('Search pages...', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)