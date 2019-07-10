from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

class NewClass(FlaskForm):
    name = StringField('Name (for example, Mr. Smith\'s class. Max 50 characters)', validators=[DataRequired(), Length(1, 50)])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Submit Class')