import time
import requests
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from threading import Thread

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host=' srv1672.hstgr.io',         # Replace with your Hostinger DB host
        user='u953503039_root',     # Replace with your Hostinger DB username
        password='Radblox!1', # Replace with your Hostinger DB password
        database='u953503039_radschedule'  # Replace with your Hostinger DB name
    )

# Fetch users from database
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, role FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return {user['username']: {'role': user['role']} for user in users}

# Fetch doctors from database
def get_doctors():
    users = get_users()
    return [user for user, details in users.items() if details['role'] == 'doctor']

# Fetch availability for doctors
def get_availability():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doctor, start_time, end_time FROM availability")
    availability = cursor.fetchall()
    cursor.close()
    conn.close()
    return {a['doctor']: (a['start_time'], a['end_time']) for a in availability}

# Fetch breaks for doctors
def get_breaks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doctor, break_end_time FROM breaks")
    breaks = cursor.fetchall()
    cursor.close()
    conn.close()
    return {b['doctor']: b['break_end_time'] for b in breaks}

# Fetch notes for doctors
def get_notes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doctor, note FROM notes")
    notes = cursor.fetchall()
    cursor.close()
    conn.close()
    return {n['doctor']: n['note'] for n in notes}

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
    users = get_users()

    if username in users:
        session['username'] = username
        session['role'] = users[username]['role']
        return redirect(url_for('dashboard'))
    return 'Invalid credentials'

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = get_indian_time()
    available_now = {}
    upcoming_scheduled = {}
    breaks = get_breaks()

    doctor_breaks = get_breaks()
    available_doctors = get_availability()
    
    for doctor, break_end in doctor_breaks.items():
        if current_time >= break_end:
            start_time, end_time = available_doctors.get(doctor, (None, None))
            if start_time and end_time:
                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
                if start_time <= current_time <= end_time:
                    available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
            del doctor_breaks[doctor]
        else:
            breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

    for doctor, (start_time, end_time) in available_doctors.items():
        start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

        if start_time <= current_time <= end_time and doctor not in doctor_breaks:
            available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
        elif start_time > current_time:
            upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    if session['role'] == 'qa_radiographer' or session['role'] == 'admin':
        doctor_notes = get_notes()
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
    
    availability_start = f'{start_date} {start_time}'
    availability_end = f'{end_date} {end_time}'

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO availability (doctor, start_time, end_time) VALUES (%s, %s, %s)", 
                   (doctor, availability_start, availability_end))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctor = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = get_indian_time() + timedelta(minutes=break_duration)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO breaks (doctor, break_end_time) VALUES (%s, %s)", 
                   (doctor, break_end_time))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/admin_control')
def admin_control():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    
    doctors = get_doctors()  # Retrieve doctor names
    users = get_users()
    doctor_notes = get_notes()
    return render_template('admin_control.html', users=users, doctor_notes=doctor_notes, doctors=doctors)

@app.route('/add_note', methods=['POST'])
def add_note():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    
    doctor = request.form['doctor']
    note = request.form['note']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO notes (doctor, note) VALUES (%s, %s)", (doctor, note))
    conn.commit()
    cursor.close()
    conn.close()

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


