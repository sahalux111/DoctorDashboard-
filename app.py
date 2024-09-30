import time
import requests
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from threading import Thread
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('193.203.184.158'),
        user=os.getenv('u953503039_root'),
        password=os.getenv('Radblox!1'),
        database=os.getenv('u953503039_radschedule')
    )

# Get doctor names from the database
def get_doctors():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE role = 'doctor'")
    doctors = [row[0] for row in cursor.fetchall()]
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
    cursor = connection.cursor()
    cursor.execute("SELECT password, role FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    connection.close()

    if user and user[0] == password:  # No password hashing
        session['username'] = username
        session['role'] = user[1]
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

    # Get doctors on break
    cursor.execute("SELECT doctor, break_end FROM doctor_breaks WHERE break_end > %s", (current_time,))
    doctor_breaks = cursor.fetchall()

    for doctor, break_end in doctor_breaks:
        breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

    # Get available doctors
    cursor.execute("SELECT doctor, start_time, end_time FROM availability WHERE start_time <= %s AND end_time >= %s", (current_time, current_time))
    available_doctors = cursor.fetchall()

    for doctor, start_time, end_time in available_doctors:
        if doctor not in breaks:
            available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')

    connection.close()

    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    if session['role'] in ['qa_radiographer', 'admin']:
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled=upcoming_scheduled)

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
    cursor.execute("REPLACE INTO availability (doctor, start_time, end_time) VALUES (%s, %s, %s)", 
                   (doctor, availability_start, availability_end))
    connection.commit()
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
    cursor.execute("REPLACE INTO doctor_breaks (doctor, break_end) VALUES (%s, %s)", 
                   (doctor, break_end_time))
    connection.commit()
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
            # Replace with your deployed app's URL
            requests.get('https://radblox.onrender.com/')
            print("Ping successful!")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(15)  # Ping every 15 seconds

if __name__ == '__main__':
    ping_thread = Thread(target=ping_app)
    ping_thread.daemon = True
    ping_thread.start()

    app.run(debug=True)
