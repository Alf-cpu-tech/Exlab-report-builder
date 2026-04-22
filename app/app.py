from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import pandas as pd
import json
import matplotlib.pyplot as plt
import io
# Additionally requires openpyxl, figure that out for when the server is a thing

# APP CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exlab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

def time_to_seconds(t):
    """Convert time value to seconds."""

    # Handle formats
    if t is None or pd.isna(t):
        return None

    # If numeric (seconds), return as float/int
    if isinstance(t, (int, float)):
        return float(t)

    # Convert pandas Timestamp to str
    if not isinstance(t, str):
        t = str(t)

    # Normalise '0 days 00:01:05'
    if "days" in t:
        t = t.split("days")[-1].strip()

    # Clean
    t = t.strip()

    try:
        h, m, s = t.split(":")
        return int(h)*3600 + int(m)*60 + float(s)
    except Exception:
        # If invalid time, return None instead of error
        return None

def read_any_spreadsheet(path):
    ext = path.split(".")[-1].lower()

    try:
        if ext == "csv":
            return pd.read_csv(path)
        else:
            return pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Failed to read file '{path}': {e}")

def process_dataset(path, dataset_id):
    """Convert uploaded raw spreadsheet into many JSON rows."""
    df = read_any_spreadsheet(path)

    # Add Logging
    print("\nRAW HEAD")
    print(df.head())
    print("========\n")

    if "t" in df.columns:
        df["t_seconds"] = df["t"].apply(time_to_seconds)
        # Drop col if crashing
        if df["t_seconds"].isna().all():
            df.drop(columns=["t_seconds"], inplace=True)

    # Store EACH row as JSON
    for _, row in df.iterrows():
        blob = json.dumps(row.to_dict())
        entry = Processed(dataset_id=dataset_id, json_data=blob)
        db.session.add(entry)

    db.session.commit()

# ROUTES

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
        flash("You must be logged in.", "warning")
        return redirect(url_for("login"))

    if request.method == 'GET':
        return render_template('upload.html')

    file = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("upload"))

    if not allowed_file(file.filename):
        flash("Invalid file type (use CSV / XLS / XLSX)", "danger")
        return redirect(url_for("upload"))

    original = secure_filename(file.filename)
    newname = f"{uuid.uuid4()}.{original.split('.')[-1]}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], newname)
    file.save(path)

    # Create Dataset entry
    dataset = Dataset(
        user_id=session['user_id'],
        filename=original,
        status="uploaded",
        metadata_=None
    )
    db.session.add(dataset)
    db.session.commit()

    # Insert many JSON rows
    try:
        process_dataset(path, dataset.id)
    except Exception as e:
        flash(f"Error processing file: {e}", "danger")
        return redirect(url_for("upload"))

    return redirect(url_for('upload_success'))

@app.route('/upload/success')
def upload_success():
    return render_template('upload_success.html')

# Dataset List

@app.route('/datasets')
def datasets():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_datasets = Dataset.query.filter_by(user_id=session['user_id']).all()
    return render_template('datasets.html', datasets=user_datasets)

#Chart Viewer

@app.route('/chart/<int:dataset_id>')
def chart(dataset_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    raw = Processed.query.filter_by(dataset_id=dataset_id).all()
    if not raw:
        return "No processed data found", 404

    # Decode all JSON rows
    decoded = [json.loads(r.json_data) for r in raw]
    df = pd.DataFrame(decoded)

    # List numeric fields
    numeric = df.select_dtypes(include='number').columns.tolist()
    if not numeric:
        return "No numeric data to plot", 400

    metric = request.args.get("metric", numeric[0])

    if metric not in numeric:
        metric = numeric[0]

    # X-axis
    if "t_seconds" in df.columns:
        x = df["t_seconds"]
    else:
        x = df.index

    # Make chart
    fig, ax = plt.subplots(figsize=(8, 4))

    # Compatibility with CSS
    line, = ax.plot(x, df[metric], marker='o')
    line.set_gid("mpl-line")
    line.set_markerfacecolor("none")
    ax.grid(color="#e0e0e0")
    for spine in ax.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(1)

    # Titles, labels
    ax.set_title(f"{metric} over time")
    ax.set_xlabel("Time")
    ax.set_ylabel(metric)

    # Save SVG to memory instead of to file (Tell Matthew at some point(optional))
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    svg = buf.getvalue()

    return render_template(
        "chart.html",
        svg=svg,
        metrics=numeric,
        selected=metric,
        dataset_id=dataset_id
    )


# MAIN

if __name__ == '__main__':
    app.run(debug=True)