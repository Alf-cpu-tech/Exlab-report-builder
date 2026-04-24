from flask import Flask, render_template, redirect, url_for, request, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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

    metric  = request.args.get("metric",  numeric[0])
    metric2 = request.args.get("metric2", "")
    clean   = request.args.get("clean",   False)
    notes   = request.args.get("notes",   "")

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

    if metric2 and metric2 in numeric:
        line2, = ax.plot(x, df[metric2], marker='s', linestyle='--')
        line2.set_gid("mpl-line2")
        line2.set_markerfacecolor("none")

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
    plt.close(fig)
    svg = buf.getvalue()

    # Get original filename for display
    dataset = Dataset.query.get(dataset_id)
    filename = dataset.filename if dataset else f"dataset_{dataset_id}"

    return render_template(
        "chart.html",
        svg=svg,
        metrics=numeric,
        selected=metric,
        selected2=metric2,
        clean=bool(clean),
        notes=notes,
        dataset_id=dataset_id,
        filename=filename,
    )

# Report Page

@app.route('/report')
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    dataset_id = request.args.get('dataset_id', type=int)
    user_datasets = Dataset.query.filter_by(user_id=session['user_id']).all()

    svg = None
    summary = None
    filename = None
    stats = None

    if dataset_id:
        raw = Processed.query.filter_by(dataset_id=dataset_id).all()
        if raw:
            decoded = [json.loads(r.json_data) for r in raw]
            df = pd.DataFrame(decoded)

            dataset = Dataset.query.get(dataset_id)
            filename = dataset.filename if dataset else f"dataset_{dataset_id}"

            # Build preview SVG (small, clean)
            numeric = df.select_dtypes(include='number').columns.tolist()
            x = df['t_seconds'] if 't_seconds' in df.columns else pd.Series(range(len(df)))

            fig, ax = plt.subplots(figsize=(6, 3))
            if "V'O2" in df.columns:
                ax.plot(x, df["V'O2"], linewidth=1.5)
                ax.set_ylabel("V'O2 (L/min)")
            elif numeric:
                ax.plot(x, df[numeric[0]], linewidth=1.5)
                ax.set_ylabel(numeric[0])
            ax.set_xlabel("Time (s)")
            ax.grid(color="#e0e0e0", linewidth=0.5)
            ax.set_title("Exercise Data Preview")
            for spine in ax.spines.values():
                spine.set_linewidth(0.8)
            fig.tight_layout()
            buf = io.StringIO()
            fig.savefig(buf, format='svg')
            plt.close(fig)
            svg = buf.getvalue()

            # Key stats
            stat_cols = ["V'O2", "HR", "RER", "V'E", "METS"]
            stats = {}
            for col in stat_cols:
                if col in df.columns:
                    stats[col] = {
                        'max': round(df[col].max(), 2),
                        'mean': round(df[col].mean(), 2),
                    }

            # Session summary
            n_rows = len(df)
            t_col = df['t_seconds'] if 't_seconds' in df.columns else None
            duration = None
            if t_col is not None:
                duration_s = int(t_col.max() - t_col.min())
                duration = f"{duration_s // 60}m {duration_s % 60}s"

            summary = {
                'filename': filename,
                'rows': n_rows,
                'duration': duration,
                'phase': df['Phase'].iloc[0] if 'Phase' in df.columns else 'N/A',
            }

    return render_template('report.html',
        svg=svg,
        summary=summary,
        stats=stats,
        datasets=user_datasets,
        selected_id=dataset_id,
    )


# PDF Export

@app.route('/report/pdf/<int:dataset_id>')
def report_pdf(dataset_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    raw = Processed.query.filter_by(dataset_id=dataset_id).all()
    if not raw:
        flash('No data found for that dataset.', 'danger')
        return redirect(url_for('report'))

    decoded = [json.loads(r.json_data) for r in raw]
    df = pd.DataFrame(decoded)

    dataset = Dataset.query.get(dataset_id)
    filename = dataset.filename if dataset else f'dataset_{dataset_id}'
    notes    = request.args.get('notes', '')

    numeric = df.select_dtypes(include='number').columns.tolist()
    x = df['t_seconds'] if 't_seconds' in df.columns else pd.Series(range(len(df)))

    fig, ax = plt.subplots(figsize=(7, 3))
    if "V'O2" in df.columns:
        ax.plot(x, df["V'O2"], linewidth=1.5, label="V'O2")
        if 'HR' in df.columns:
            ax2 = ax.twinx()
            ax2.plot(x, df['HR'], linewidth=1.2, color='tomato', linestyle='--', label='HR')
            ax2.set_ylabel('HR (bpm)', color='tomato', fontsize=8)
        ax.set_ylabel("V'O2 (L/min)", fontsize=8)
    elif numeric:
        ax.plot(x, df[numeric[0]], linewidth=1.5)
        ax.set_ylabel(numeric[0], fontsize=8)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.set_title('Exercise Data', fontsize=9)
    ax.grid(color='#e0e0e0', linewidth=0.5)
    fig.tight_layout()
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=120)
    plt.close(fig)
    img_buf.seek(0)

    #Build PDF
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Heading1'], fontSize=16, spaceAfter=6)
    sub_style   = ParagraphStyle('Sub',    parent=styles['Normal'],   fontSize=9,  textColor=colors.grey)
    label_style = ParagraphStyle('Label',  parent=styles['Normal'],   fontSize=9,  fontName='Helvetica-Bold')
    body_style  = ParagraphStyle('Body',   parent=styles['Normal'],   fontSize=9)

    story = []

    # Header
    story.append(Paragraph('ExLab Report Builder', title_style))
    story.append(Paragraph(f'File: {filename} &nbsp;&nbsp; User: {session["username"]}', sub_style))
    story.append(Spacer(1, 0.3*cm))

    # Session summary
    n_rows = len(df)
    t_col = df['t_seconds'] if 't_seconds' in df.columns else None
    duration = '—'
    if t_col is not None:
        d_s = int(t_col.max() - t_col.min())
        duration = f'{d_s // 60}m {d_s % 60}s'
    phase = df['Phase'].iloc[0] if 'Phase' in df.columns else 'N/A'

    summary_data = [
        ['Filename', filename],
        ['Phase',    phase],
        ['Breaths',  str(n_rows)],
        ['Duration', duration],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm, 10*cm])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#444444')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8f8f8'), colors.white]),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
        ('TOPPADDING',  (0,0), (-1,-1), 4),
        ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4*cm))

    # Chart
    story.append(Paragraph('Exercise Chart', styles['Heading2']))
    rl_img = RLImage(img_buf, width=15*cm, height=6.5*cm)
    story.append(rl_img)
    story.append(Spacer(1, 0.4*cm))

    # Stats table
    stat_cols = ["V'O2", 'HR', 'RER', "V'E", 'METS']
    present   = [c for c in stat_cols if c in df.columns]
    if present:
        story.append(Paragraph('Key Statistics', styles['Heading2']))
        header = ['Metric', 'Max', 'Mean', 'Min']
        rows   = [header]
        for col in present:
            rows.append([
                col,
                str(round(df[col].max(),  2)),
                str(round(df[col].mean(), 2)),
                str(round(df[col].min(),  2)),
            ])
        stats_table = Table(rows, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f8f8'), colors.white]),
            ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
            ('BOTTOMPADDING',(0,0), (-1,-1), 5),
            ('TOPPADDING',  (0,0), (-1,-1), 5),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.4*cm))

    # Notes
    if notes.strip():
        story.append(Paragraph('Notes / Comments', styles['Heading2']))
        story.append(Paragraph(notes.replace('\n', '<br/>'), body_style))
        story.append(Spacer(1, 0.2*cm))

    doc.build(story)
    pdf_buf.seek(0)

    inline   = request.args.get('inline', '0') == '1'
    disposition = 'inline' if inline else f'attachment; filename="report_{filename}.pdf"'
    response = make_response(pdf_buf.read())
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = disposition
    return response


# MAIN

if __name__ == '__main__':
    app.run(debug=True)