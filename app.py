import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Use environment variable for DATABASE_URL
DATABASE_URL = 'postgresql://sahal:<Y1VxilKjWihuvtrWTgVx7g>@fire-quokka-3404.j77.aws-ap-south-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full'


# Function to get a database connection using psycopg2
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='verify-full')
    return conn

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user and user['password'] == password:
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(url_for('dashboard'))

    return 'Invalid credentials'

# Additional routes and logic...
# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = get_indian_time()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch doctor breaks from the database
    cursor.execute("SELECT doctor, break_end FROM breaks WHERE break_end > %s", (current_time,))
    doctor_breaks = cursor.fetchall()

    for row in doctor_breaks:
        breaks[row['doctor']] = row['break_end'].strftime('%Y-%m-%d %H:%M')

    # Fetch availability
    cursor.execute("SELECT doctor, start_time, end_time FROM availability")
    availabilities = cursor.fetchall()

    for row in availabilities:
        start_time = row['start_time']
        end_time = row['end_time']

        if start_time <= current_time <= end_time and row['doctor'] not in doctor_breaks:
            available_now[row['doctor']] = end_time.strftime('%Y-%m-%d %H:%M')
        elif start_time > current_time:
            upcoming_scheduled[row['doctor']] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

    conn.close()

    # Restrict data for doctors
    if session['role'] == 'doctor':
        username = session['username']
        available_now = {username: available_now.get(username)}
        breaks = {username: breaks.get(username)}
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled={})

    if session['role'] == 'qa_radiographer' or session['role'] == 'admin':
        return render_template('dashboard.html', available_now=available_now, breaks=breaks, upcoming_scheduled=upcoming_scheduled)

# Set availability
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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPSERT INTO availability (doctor, start_time, end_time) VALUES (%s, %s, %s)",
        (doctor, availability_start, availability_end)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# Take break
@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))

    doctor = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = get_indian_time() + timedelta(minutes=break_duration)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPSERT INTO breaks (doctor, break_end) VALUES (%s, %s)", (doctor, break_end_time))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# Admin control
@app.route('/admin_control')
def admin_control():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE role = 'doctor'")
    doctors = cursor.fetchall()

    cursor.execute("SELECT * FROM notes")
    doctor_notes = cursor.fetchall()

    conn.close()
    return render_template('admin_control.html', doctors=doctors, doctor_notes=doctor_notes)

# Add note
@app.route('/add_note', methods=['POST'])
def add_note():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    note = request.form['note']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPSERT INTO notes (doctor, note) VALUES (%s, %s)", (doctor, note))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_control'))

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

# Ping app
def ping_app():
    while True:
        try:
            requests.get('https://radblox.onrender.com/')
            print("Ping successful!")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(15)

if __name__ == '__main__':
    ping_thread = Thread(target=ping_app)
    ping_thread.daemon = True
    ping_thread.start()

    app.run(debug=True)
