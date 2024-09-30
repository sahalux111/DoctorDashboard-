import time
import requests
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from threading import Thread

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection configuration
def get_db_connection():
    return mysql.connector.connect(
        host='127.0.0.1:3306',  # e.g., 'mysql-01.hosting.com'
        user='u953503039_root',
        password='Radblox!1',
        database='u953503039_radschedule'
    )

# Adjust time zone to Indian Standard Time (UTC+5:30)
def get_indian_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Query the database for the user
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    # Close the database connection
    cursor.close()
    connection.close()

    # Validate user credentials
    if user and user['password'] == password:
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    return 'Invalid credentials'

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = get_indian_time()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get all doctor availability
    cursor.execute("SELECT * FROM availability")
    availability_records = cursor.fetchall()

    for record in availability_records:
        start_time = datetime.strptime(record['start_time'], '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(record['end_time'], '%Y-%m-%d %H:%M')
        if start_time <= current_time <= end_time:
            available_now[record['doctor']] = end_time.strftime('%Y-%m-%d %H:%M')

    # Get all breaks
    cursor.execute("SELECT * FROM breaks")
    break_records = cursor.fetchall()

    for record in break_records:
        break_end = datetime.strptime(record['break_end'], '%Y-%m-%d %H:%M')
        if current_time < break_end:
            breaks[record['doctor']] = break_end.strftime('%Y-%m-%d %H:%M')

    # Close database connection
    cursor.close()
    connection.close()

    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    if session['role'] == 'qa_radiographer' or session['role'] == 'admin':
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled=upcoming_scheduled)

# Admin Control route to update availability
@app.route('/set_availability', methods=['POST'])
def set_availability():
    if 'username' not in session:
        return redirect(url_for('index'))

    doctor = session['username']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    connection = get_db_connection()
    cursor = connection.cursor()

    # Insert or update availability
    cursor.execute("""
        REPLACE INTO availability (doctor, start_time, end_time)
        VALUES (%s, %s, %s)
    """, (doctor, start_time, end_time))
    connection.commit()

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
            # Replace with your deployed app's URL
            requests.get('https://radblox.onrender.com/')
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

  
