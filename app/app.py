from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import pandas as pd

# APP CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exlab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# MODELS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String)
    status = db.Column(db.String)
    metadata_ = db.Column(db.Integer)


class Processed(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    json_data = db.Column(db.Text)


with app.app_context():
    db.create_all()

# HELPERS

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ROUTES - AUTH

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not username or not password:
            flash('Username and password are required.', 'danger')
        elif len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'danger')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('welcome'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        flash('Please log in to access that page.', 'warning')
        return redirect(url_for('login'))
    return render_template('welcome.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash("You must be logged in to upload.", "warning")
        return redirect(url_for("login"))

    if request.method == 'GET':
        return render_template('upload.html')

    file = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("upload"))

    if not allowed_file(file.filename):
        flash("Invalid file type. Use .xls/.xlsx/.csv", "danger")
        return redirect(url_for("upload"))

    # Save uploaded file
    original_filename = secure_filename(file.filename)
    generated_name = f"{uuid.uuid4()}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], generated_name)
    file.save(filepath)

    # Insert into dataset table
    dataset = Dataset(
        user_id=session['user_id'],
        filename=original_filename,
        status="uploaded",
        metadata_=None
    )
    db.session.add(dataset)
    db.session.commit()
    return redirect(url_for('upload_success'))

    # Convert to JSON
    try:
        df = pd.read_excel(filepath)
        json_data = df.to_json(orient="records")
    except Exception as e:
        flash(f"Error processing spreadsheet: {e}", "danger")
        return redirect(url_for("upload"))

    # Insert JSON into processed table
    processed = Processed(
        dataset_id=dataset.id,
        json_data=json_data
    )
    db.session.add(processed)
    db.session.commit()

    return render_template(
        "success.html",
        filename=original_filename,
        dataset_id=dataset.id,
        processed_id=processed.id
    )
@app.route('/upload/success')
def upload_success():
    return render_template('upload_success.html')


# MAIN

if __name__ == '__main__':
    app.run(debug=True)