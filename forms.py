from flask_wtf import Form
from wtforms import PasswordField, StringField
from wtforms.validators import Email, Length, EqualTo, DataRequired


class LoginForm(Form):
    email = StringField('email', validators=[DataRequired(), Email()])
    password = StringField('password', validators=[DataRequired()])


class SignupForm(Form):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=25)])
    password = PasswordField('Password', [
        DataRequired()])
    
    email = StringField('Email', validators=[DataRequired(), Length(min=5, max=35), Email()])