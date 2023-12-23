from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField, FileField, IntegerField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


# WTForm for creating a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


# Create a form to register new users
class RegisterForm(FlaskForm):
    usn = StringField("UserID", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


# Create a form to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


class CommentForm(FlaskForm):
    comment_text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


class OnlineClassForm(FlaskForm):
    name = StringField('Teacher Name', validators=[DataRequired()])
    class_link = StringField('Class Link', validators=[DataRequired(), URL()])
    start_time = StringField('Class Starts At:', validators=[DataRequired()])
    end_time = StringField('Ends At:', validators=[DataRequired()])
    branch = SelectField("Branch", choices=["CSE", "CSE-AIML", "ME", "IS", "Civil"],
                                validators=[DataRequired()])
    section = SelectField("Section", choices=["✘", "A", "B", "C", "D", "E"],
                              validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired()])
    feedback_link = StringField('Feedback Link', validators=[URL()])
    submit = SubmitField('Submit')


class StudyMaterial(FlaskForm):
    img = StringField("Material Image URL", validators=[DataRequired(), URL()])
    title = StringField("Title", validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Submit')


class AttendanceForm(FlaskForm):
    usn = StringField("USN", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    branch = StringField("Branch", validators=[DataRequired()])
    section = StringField("Section", validators=[DataRequired()])
    attedance = IntegerField("Attedance", validators=[DataRequired()])
    submit = SubmitField('Submit')
