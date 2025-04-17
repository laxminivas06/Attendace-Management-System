from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import logging
from functools import wraps
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
STUDENTS_FILE = 'students.json'
ATTENDANCE_FILE = 'attendance.json'
ADMIN_CREDENTIALS = {'username': 'admin', 'password': 'password'}  # Change before production

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --------------------- Helpers ---------------------

# Load data from JSON files
def load_data(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Error loading {filename}: {e}")
        return {}

def save_data(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving to {filename}: {e}")
        return False

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return wrapper

# --------------------- Routes ---------------------

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['username'] = username
            return redirect(request.args.get('next') or url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    students = load_data(STUDENTS_FILE)
    attendance = load_data(ATTENDANCE_FILE)
    return render_template('dashboard.html', students=students, attendance=attendance)

@app.route('/manage_students', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_students():
    if request.method == 'GET':
        students = load_data(STUDENTS_FILE)
        return render_template('manage_students.html', students=students)

    students = load_data(STUDENTS_FILE)

    if request.method == 'POST':
        student_id = request.form.get('id')
        student_name = request.form.get('name')
        student_contact = request.form.get('contact')

        if not all([student_id, student_name, student_contact]):
            return jsonify(success=False, error="All fields are required.")

        if student_id in students:
            return jsonify(success=False, error="Student ID already exists.")

        students[student_id] = {
            'name': student_name,
            'contact': student_contact
        }

        success = save_data(STUDENTS_FILE, students)
        return jsonify(success=success, error=None if success else "Failed to save student data.")

    if request.method == 'DELETE':
        data = request.get_json()
        student_id = data.get('id')

        if not student_id:
            return jsonify(success=False, error="Missing student ID.")

        if student_id not in students:
            return jsonify(success=False, error="Student not found.")

        del students[student_id]
        success = save_data(STUDENTS_FILE, students)
        return jsonify(success=success, error=None if success else "Failed to delete student.")

@app.route('/get_students')
@login_required
def get_students():
    students = load_data(STUDENTS_FILE)
    return jsonify(students)

@app.route('/save_attendance', methods=['POST'])
@login_required
def save_attendance():
    try:
        data = request.get_json()
        day = data.get('day')
        students = data.get('students')
        date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

        if not all([day, students]):
            return jsonify(success=False, error=" Missing day or student data.")

        attendance = load_data(ATTENDANCE_FILE)
        attendance[day] = {
            'date': date,
            'students': students
        }

        success = save_data(ATTENDANCE_FILE, attendance)
        return jsonify(success=success, error=None if success else "Failed to save attendance.")

    except Exception as e:
        logging.error(f"Error saving attendance: {e}")
        return jsonify(success=False, error=str(e))

@app.route('/get_attendance')
@login_required
def get_attendance():
    try:
        attendance = load_data(ATTENDANCE_FILE)
        return jsonify(attendance)
    except Exception as e:
        logging.error(f"Error loading attendance: {e}")
        return jsonify(success=False, error=str(e))

@app.route('/manage_attendance', methods=['GET', 'POST'])
@login_required
def manage_attendance():
    students = load_data(STUDENTS_FILE)
    attendance = load_data(ATTENDANCE_FILE)

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        filtered_attendance = {}

        if student_id:
            for day, record in attendance.items():
                if student_id in record['students']:
                    student_data = record['students'][student_id]
                    if day not in filtered_attendance:
                        filtered_attendance[day] = {'date': record['date'], 'students': []}
                    filtered_attendance[day]['students'].append({
                        'id': student_id,
                        'name': students[student_id]['name'],  # Get student name from students.json
                        'status': student_data['status'],
                        'interaction': student_data['interaction'],
                        'remarks': student_data['remarks']
                    })

            return render_template('manage_attendance.html', attendance=filtered_attendance, students=students)

    return render_template('manage_attendance.html', attendance=attendance, students=students)

@app.route('/update_attendance', methods=['POST'])
@login_required
def update_attendance():
    try:
        data = request.get_json()
        day = data.get('day')
        students = data.get('students')
        date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

        if not all([day, students]):
            return jsonify(success=False, error="Missing required data.")

        attendance = load_data(ATTENDANCE_FILE)
        attendance[day] = {
            'date': date,
            'students': students
        }

        success = save_data(ATTENDANCE_FILE, attendance)
        return jsonify(success=success, error=None if success else "Failed to update attendance.")

    except Exception as e:
        logging.error(f"Error updating attendance: {e}")
        return jsonify(success=False, error=str(e))

# --------------------- App Start ---------------------

if __name__ == '__main__':
    if not os.path.exists(STUDENTS_FILE):
        save_data(STUDENTS_FILE, {})
    if not os.path.exists(ATTENDANCE_FILE):
        save_data(ATTENDANCE_FILE, {})

    app.run(debug=True)