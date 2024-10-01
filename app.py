import time
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from threading import Thread
import mysql.connector  # MySQL Connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration for Hostinger MySQL
db_config = {
    'host': 'srv1672.hstgr.io',
    'user': 'u953503039_root',
    'password': 'Radblox!1',
    'database': 'u953503039_radschedule'
}

# Helper function to create a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Function to get a list of doctor names from the database
def get_doctors():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE role = 'doctor'")
    doctors = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return doctors

# Adjust time zone to Indian Standard Time (UTC+5:30)
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
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user and user['password'] == password:  # Direct password check (no hashing)
        session['username'] = username
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    return 'Invalid credentials'

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = get_indian_time()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    connection = get_db_connection()
    cursor = connection.cursor()

    # Query for doctor breaks
    cursor.execute("SELECT doctor, break_end FROM doctor_breaks")
    doctor_breaks = cursor.fetchall()

    for doctor, break_end in doctor_breaks:
        break_end = datetime.strptime(break_end, '%Y-%m-%d %H:%M')
        if current_time >= break_end:
            # Remove the doctor from breaks once the break ends
            cursor.execute("DELETE FROM doctor_breaks WHERE doctor = %s", (doctor,))
        else:
            breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

    # Query for available doctors
    cursor.execute("SELECT doctor, start_time, end_time FROM doctor_availability")
    doctor_availability = cursor.fetchall()

    for doctor, start_time, end_time in doctor_availability:
        start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

        if start_time <= current_time <= end_time and doctor not in breaks:
            available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
        elif start_time > current_time:
            upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

    cursor.close()
    connection.close()

    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    if session['role'] == 'qa_radiographer' or session['role'] == 'admin':
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT doctor, note FROM doctor_notes")
        doctor_notes = dict(cursor.fetchall())
        cursor.close()
        connection.close()
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled=upcoming_scheduled, doctor_notes=doctor_notes)

@app.route('/select_availability')
def select_availability():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctors = get_doctors()  # Retrieve doctor names
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
    
    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
    availability_end = datetime.strptime(f'{end_date} {end_time}', '%Y-%m-%d %H:%M')

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("REPLACE INTO doctor_availability (doctor, start_time, end_time) VALUES (%s, %s, %s)",
                   (doctor, availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M')))
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('dashboard'))

@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))

    doctor = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = get_indian_time() + timedelta(minutes=break_duration)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("REPLACE INTO doctor_breaks (doctor, break_end) VALUES (%s, %s)", (doctor, break_end_time.strftime('%Y-%m-%d %H:%M')))
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('dashboard'))

@app.route('/add_note', methods=['POST'])
def add_note():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    note = request.form['note']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("REPLACE INTO doctor_notes (doctor, note) VALUES (%s, %s)", (doctor, note))
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('admin_control'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

def ping_app():
    while True:
        try:
            # Replace with your deployed app's URL
            requests.get('https://your-app-url.onrender.com/')
            print("Ping successful!")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(15)  # Ping every 15 seconds

if __name__ == '__main__':
    # Start the pinging in a separate thread
    ping_thread = Thread(target=ping_app)
    ping_thread.daemon = True
    ping_thread.start()

    app.run(debug=True)

