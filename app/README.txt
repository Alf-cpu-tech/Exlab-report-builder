Flask Auth App — Login, Register & Welcome
==========================================

A basic user authentication web app built with Flask and SQLite.


FEATURES
--------
- User registration with username and password validation
- Secure login with hashed passwords (Werkzeug)
- Protected welcome page — redirects to login if not authenticated
- Sticky header on every page with logout button when logged in
- Flash messages for success/error feedback
- SQLite database auto-created on first run (no setup needed)


PROJECT STRUCTURE
-----------------
Project for group/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .gitignore              # Excludes DB, venv, cache, .env files
├── README.txt              # This file
└── templates/
    ├── base.html           # Shared layout with header and flash messages
    ├── login.html          # Login page
    ├── register.html       # Registration page
    └── welcome.html        # Protected welcome page (requires login)


INSTALLING PYTHON
-----------------
If you do not have Python installed:

1. Go to https://www.python.org/downloads/ and download the latest
   Python 3 installer for your operating system.

2. Run the installer.
   IMPORTANT: On Windows, tick "Add Python to PATH" before clicking Install.

3. Verify the installation by opening a terminal (Command Prompt or
   PowerShell on Windows, Terminal on Mac/Linux) and running:

   python --version

   You should see something like: Python 3.x.x


HOW TO RUN
----------

1. Make sure Python 3 is installed (see INSTALLING PYTHON above).

2. Open a terminal and navigate to the project folder:

   cd "Project for group"

3. Create a virtual environment (keeps dependencies isolated):

   python -m venv .venv

4. Activate the virtual environment:

   Windows (PowerShell):
     .venv\Scripts\Activate.ps1

   Windows (Command Prompt):
     .venv\Scripts\activate.bat

   Mac / Linux:
     source .venv/bin/activate

   Your terminal prompt will change to show (.venv) when active.

5. Install dependencies:

   python -m pip install -r requirements.txt

6. Start the app:

   python app.py

7. Open your browser and go to:

   http://127.0.0.1:5000

8. Register a new account, then log in to reach the welcome page.

   To stop the app, press Ctrl+C in the terminal.

NOTE: Every time you return to work on the project, re-activate the
virtual environment (step 4) before running the app.


DATABASE
--------
- SQLite is used as the database — no installation required.
- The database file (users.db) is automatically created inside the
  instance/ folder on first run.
- To view registered users, run:

  python.exe -c "import sqlite3; conn = sqlite3.connect('instance/users.db'); print(conn.execute('SELECT id, username FROM user').fetchall()); conn.close()"

- Passwords are stored as secure hashes, never in plain text.
