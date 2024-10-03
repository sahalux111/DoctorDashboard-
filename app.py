import time
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from threading import Thread
import mysql.connector
import logging  # Logging for better error tracking

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Database configuration
db_config = {
    'host': 'srv1672.hstgr.io',
    'user': 'u953503039_root',
    'password': 'Radblox!1',
    'database': 'u953503039_radschedule'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        return None

def get_doctors():
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT username FROM users WHERE role = 'doctor'")
        doctors = [row[0] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        logging.error(f"Error fetching doctors: {err}")
        doctors = []
    finally:
        cursor.close()
        connection.close()
    
    return doctors

def get_indian_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    connection = get_db_connection()
    if not connection:
        return 'Database connection error'

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    except mysql.connector.Error as err:
        logging.error(f"Login error: {err}")
        return 'Internal server error'
    finally:
        cursor.close()
        connection.close()

    if user and user['password'] == password:  # Replace with hashed password verification
        session['username'] = username
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials', 'danger')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = get_indian_time()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed!")
        return 'Database connection error'

    try:
        cursor = connection.cursor()

        # Query for doctor breaks
        cursor.execute("SELECT doctor, break_end FROM doctor_breaks")
        doctor_breaks = cursor.fetchall()

        for doctor, break_end in doctor_breaks:
            break_end = datetime.strptime(break_end, '%Y-%m-%d %H:%M')
            if current_time >= break_end:
                cursor.execute("DELETE FROM doctor_breaks WHERE doctor = %s", (doctor,))
            else:
                breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

        # Query for doctor availability
        cursor.execute("SELECT doctor, start_time, end_time FROM doctor_availability")
        doctor_availability = cursor.fetchall()

        for doctor, start_time, end_time in doctor_availability:
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

            if start_time <= current_time <= end_time and doctor not in breaks:
                available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
            elif start_time > current_time:
                upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

    except Exception as e:
        logging.error(f"Error querying doctor availability or breaks: {e}")
        return 'Internal server error', 500
    finally:
        cursor.close()
        connection.close()

    # If admin or QA role, fetch doctor notes
    if session['role'] in ['qa_radiographer', 'admin']:
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT doctor, note FROM doctor_notes")
            doctor_notes = dict(cursor.fetchall())
        except Exception as e:
            logging.error(f"Error fetching doctor notes: {e}")
            doctor_notes = {}  # Handle case when no notes are found or query fails
        finally:
            cursor.close()
            connection.close()

        return render_template(
            'dashboard.html', 
            available_now=available_now, 
            breaks=breaks, 
            upcoming_scheduled=upcoming_scheduled, 
            doctor_notes=doctor_notes
        )

    # For non-admin roles (doctors), restrict dashboard content
    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    # Handle unexpected roles
    logging.error(f"Unauthorized access attempt by role: {session['role']}")
    return 'Unauthorized', 403

@app.route('/select_availability')
def select_availability():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctors = get_doctors()
    return render_template('select_availability.html', doctors=doctors)

@app.route('/set_availability', methods=['POST'])
def set_availability():
    if 'username' not in session:
        return redirect(url_for('index'))

    doctor = session['username']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_date = request.form['end_date']
    end_time = request.form['end_time']

    try:
        availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
        availability_end = datetime.strptime(f'{end_date} {end_time}', '%Y-%m-%d %H:%M')
    except ValueError as e:
        logging.error(f"Date format error: {e}")
        return 'Invalid date format'

    connection = get_db_connection()
    if not connection:
        return 'Database connection error'

    try:
        cursor = connection.cursor()
        cursor.execute("REPLACE INTO doctor_availability (doctor, start_time, end_time) VALUES (%s, %s, %s)",
                       (doctor, availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M')))
        connection.commit()
    except mysql.connector.Error as err:
        logging.error(f"Error setting availability: {err}")
        return 'Internal server error'
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

def ping_app():
    while True:
        try:
            requests.get('https://your-app-url.onrender.com/')
            logging.info("Ping successful")
        except Exception as e:
            logging.error(f"Ping failed: {e}")
        time.sleep(15)

if __name__ == '__main__':
    ping_thread = Thread(target=ping_app)
    ping_thread.daemon = True
    ping_thread.start()

    app.run(debug=True)
