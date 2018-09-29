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