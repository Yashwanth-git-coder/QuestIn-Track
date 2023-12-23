from datetime import datetime, timedelta, date, timezone
from sqlalchemy import event
from flask import Flask, abort, render_template, redirect, url_for, flash, request, send_file, make_response, send_from_directory
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
import csv
from io import BytesIO
from flask_socketio import SocketIO, send
from pytz import utc
import openai
import os
from fpdf import FPDF
from dotenv import load_dotenv
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, OnlineClassForm, StudyMaterial, AttendanceForm




app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_key = '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'

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)

#Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_fun(*args, **kwargs):
        if current_user.is_authenticated:  # if a user is logged in
            if current_user.id != 1:  # and is not the admin
                return abort(403)
        else:  # random stranger
            return abort(403)
        return f(*args, **kwargs)  # only option left is the admin
    return decorated_fun


# For adding profile images to the comment section
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")


# Create a User table for all your registered users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    usn = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")
    attendance_count = db.Column(db.Integer, default=0)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # *******Add child relationship*******#
    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


# class Attendance(db.Model):
#     usn = db.Column(db.String(100), unique=True)
#     name = db.Column(db.String(100))
#     branch = db.Column(db.String(100))
#     section = db.Column(db.String(100))
#     Attendance = db.Column(db.Integer)


class Materials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    file = db.Column(db.String(250), nullable=False)
    # date = db.Column(db.String(250), nullable=False)
    last_access_time = db.Column(db.DateTime, default=datetime.utcnow)



with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
# Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if user email is already present in the database.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            usn=form.usn.data,
            email=form.email.data,
            name=form.name.data,  # Make sure this is correctly set from the form data
            password=hash_and_salted_password,
        )

        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('enter_class'))

    return render_template("login.html", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('start_page'))

@app.route('/')
def start_page():
    return render_template("index.html")


@app.route('/home')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
# Add a POST method to be able to post comments
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    # Add the CommentForm to the route
    comment_form = CommentForm()
    # Only allow logged-in users to comment on posts
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,  # Make sure you're assigning the current logged-in user as the author
            date=date.today().strftime("%B %d, %Y")
        )

        db.session.add(new_post)
        db.session.commit()
        print(current_user)
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)



@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/contact")
def contact():
    return render_template("contact.html")



@app.route("/class")
def enter_class():
    return render_template("index2.html")

@app.route('/scheduling', methods=["GET", "POST"])
def add_class():
    form = OnlineClassForm()
    if form.validate_on_submit():
        with open("cafe-data.csv", mode="a", encoding='utf-8') as csv_file:
            csv_file.write(f"\n{form.name.data},"
                           f"{form.class_link.data},"
                           f"{form.start_time.data},"
                           f"{form.end_time.data},"
                           f"{form.branch.data},"
                           f"{form.section.data},"
                           f"{form.subject.data},"
                           f"{form.feedback_link.data}")
        return redirect(url_for('view_classes'))
    return render_template('add.html', form=form)

@app.route('/scheduled-classes')
def view_classes():
    with open('cafe-data.csv', newline='', encoding='utf-8') as csv_file:
        csv_data = csv.reader(csv_file, delimiter=',')
        list_of_rows = []
        for row in csv_data:
            list_of_rows.append(row)
    return render_template('cafes.html', cafes=list_of_rows)

@app.route('/study-metirial')
def study_material():
    materials = Materials.query.all()
    # result = db.session.execute(select(Materials))
    # materials = result.scalars().all()
    return render_template("matirial.html", all_materials=materials)


@app.route('/upload-document', methods=["GET", "POST"])
def upload_document():
    form = StudyMaterial()
    if form.validate_on_submit():
        try:
            img = form.img.data  # Assuming img is a URL or path to an image
            title = form.title.data
            file = form.file.data

            new_material = Materials(
                img=img,
                title=title,
                file=file.filename
            )
            db.session.add(new_material)
            db.session.commit()

            file.save(f'static/uploads/{file.filename}')
            flash('Document uploaded successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template("upload_material.html", form=form)


# @app.route('/download/<int:material_id>', methods=['GET'])
# def download_material(material_id):
#     material = Materials.query.get_or_404(material_id)
#
#     file_data = material.file.encode('utf-8')
#   # Assuming 'file' contains the file content as bytes
#
#     file_obj = BytesIO(file_data)
#     file_obj.seek(0)  # Move the cursor to the start of the BytesIO object
#
#     return send_file(
#         file_obj,
#         mimetype='application/octet-stream',
#         as_attachment=True,
#         download_name=f'material_{material_id}.file'  # Use a generic file name
#     )

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    with app.app_context():
        uploads_dir = 'static/uploads'
        return send_from_directory(uploads_dir, filename, as_attachment=True)

# --------------------------------------- chat bot --------------------------------- #

@app.route('/chat', methods=["GET", "POST"])
def chat():
    return render_template("chat.html")


@app.route('/chatbot', methods=["POST"])
def chatbot():
    user_input = request.form['message']
    prompt = f"User: {user_input}\nChatbot:"
    chat_history = []
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        temperature=0.5,
        max_tokens=60,
        top_p=1,
        frequency_penalty=0,
        stop=["\nUser:", "\nChatbot: "]
    )

    bot_response = response.choices[0].text.strip()

    chat_history.append(f"User: {user_input}\nChatbot: {bot_response}")

    return render_template(
        "chatbot.html",
        user_input=user_input,
        bot_response=bot_response,
    )



# ----------------------------------Attendance Report--------------------------------- #

@app.route('/attendance-report', methods=['GET', 'POST'])
# @login_required
def attendance_report():
    user = User.query.all()
    return render_template("attedence_report.html", user_elements=user)

@app.route('/access_material/<int:material_id>')
@login_required  # Uncomment this line to enforce authentication
def access_material(material_id):
    material = Materials.query.get_or_404(material_id)

    # Check if the current user has accessed this material within the time limit
    if material_access_within_time_limit(material):
        update_attendance(current_user)
        return f'Attendance updated for {current_user.name}!'
    else:
        return 'Time limit exceeded. Attendance update disabled.'

def material_access_within_time_limit(material):
    current_time = datetime.now(timezone.utc)  # Get the current time in UTC timezone

    # Assuming material.last_access_time is timezone-aware or in UTC
    material_access_time = material.last_access_time

    if material_access_time:
        time_difference = current_time - material_access_time.replace(tzinfo=timezone.utc)
        return time_difference <= timedelta(minutes=10)
    else:
        return False
# Update user's attendance
def update_attendance(user):
    user.attendance_count += 1
    db.session.commit()


# -------------------------------------------------------------------------------------- #

@app.route('/profile')
def profile():
    return render_template("profile.html")

# Function to generate a report using OpenAI's API
def generate_report_with_ai(topic):
    prompt = f"Generate a report on {topic}."
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=200
    )
    return response.choices[0].text


# Function to generate PDF from report content
def generate_pdf(content, topic):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report on {topic}", ln=True, align="C")
    pdf.multi_cell(0, 10, txt=content)

    # Save the PDF to memory
    pdf_output = pdf.output(dest='S')
    return pdf_output


# Route to render the form for topic input
@app.route('/report')
def report():
    return render_template('prompts.html')

@app.route('/generate_report', methods=['POST'])
def generate_report():
    topic = request.form['topic']

    # Generate the report based on the topic
    report = generate_report_with_ai(topic)

    # Convert the report to PDF using FPDF
    pdf_data = generate_pdf(report, topic)

    # Pass the PDF data and topic to the template
    return render_template('download.html', pdf_data=pdf_data, topic=topic)



# Route to handle report generation and initiate download
@app.route('/generate_report_and_download', methods=['POST'])
def generate_report_and_download():
    topic = request.form['topic']  # Get the topic from the form

    # Generate the report based on the topic using OpenAI's API
    report = generate_report_with_ai(topic)

    # Convert the report to PDF using FPDF
    pdf_data = generate_pdf(report, topic)

    # Create a response to trigger the file download
    response = make_response(pdf_data)
    response.headers["Content-Disposition"] = f"attachment; filename={topic}_report.pdf"
    response.headers["Content-Type"] = "application/pdf"

    return response



if __name__ == "__main__":
    app.run(debug=True)
