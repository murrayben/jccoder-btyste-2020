from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import DateTimeField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from ..models import Class, Permission, User

class NewClass(FlaskForm):
    name = StringField('Name (for example, Mr. Smith\'s class. Max 50 characters)', validators=[DataRequired(), Length(1, 50)])
    description = TextAreaField('Description (Optional)', validators=[Optional()])
    submit = SubmitField('Submit Class')

class AssignmentForm(FlaskForm):
    def __init__(self, class_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.students.choices = [(student.id, student.username) for student in Class.query.get(class_id).students.all()]

    def validate_due_date(form, field):
        if field.data < datetime.utcnow():
            raise ValidationError('Due date cannot be set to a past date.')
    students = SelectMultipleField('Students', validators=[DataRequired(message="Please select one or more students.")], coerce=int)
    due_date = DateTimeField('Due date', validators=[DataRequired(message="Please enter a valid date.")], format="%d-%m-%Y")
    submit = SubmitField('Assign')