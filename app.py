

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pywhatkit

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Simulated database
users = {
    'admin': {'password': generate_password_hash('adminpassword'), 'role': 'admin'},
    'SahalTest': {'password': generate_password_hash('1234'), 'role': 'doctor', 'whatsapp_number': '+918593969452'},
    'DrArun': {'password': generate_password_hash('1234'), 'role': 'doctor', 'whatsapp_number': '+919544950920'},
    'DrTest': {'password': generate_password_hash('1234'), 'role': 'doctor', 'whatsapp_number': '+918593064956'}
}

available_doctors = {}
doctor_breaks = {}

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username in users and check_password_hash(users[username]['password'], password):
        session['username'] = username
        session['role'] = users[username]['role']
        return redirect(url_for('dashboard'))
    return 'Invalid credentials'

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    current_time = datetime.now()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    for doctor, break_end in doctor_breaks.items():
        if current_time >= break_end:
            # Break is over, move the doctor back to available
            start_time, end_time = available_doctors.get(doctor, (None, None))
            if start_time and end_time:
                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
                if start_time <= current_time <= end_time:
                    available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
            del doctor_breaks[doctor]
        else:
            # Break is ongoing
            breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

    for doctor, (start_time, end_time) in available_doctors.items():
        start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

        if start_time <= current_time <= end_time and doctor not in doctor_breaks:
            available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
        elif start_time > current_time:
            upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

    return render_template('dashboard.html', available_now=available_now, upcoming_scheduled=upcoming_scheduled, breaks=breaks)

@app.route('/select_availability')
def select_availability():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    return render_template('select_availability.html')

@app.route('/set_availability', methods=['POST'])
def set_availability():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctor = session['username']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    
    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M')

    available_doctors[doctor] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('dashboard'))

@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctor = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = datetime.now() + timedelta(minutes=break_duration)

    doctor_breaks[doctor] = break_end_time

    return redirect(url_for('dashboard'))

@app.route('/admin_control')
def admin_control():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    
    return render_template('admin_control.html', users=users)

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M')

    available_doctors[doctor] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('admin_control'))

@app.route('/update_break', methods=['POST'])
def update_break():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    break_duration = int(request.form['break_duration'])
    break_end_time = datetime.now() + timedelta(minutes=break_duration)

    doctor_breaks[doctor] = break_end_time

    return redirect(url_for('admin_control'))

@app.route('/send_whatsapp', methods=['POST'])
def send_whatsapp():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    pacs = request.form['pacs']
    number_of_cases = request.form['number_of_cases']

    # Construct the message
    message_body = f"Hello {doctor}, you have been assigned {number_of_cases} cases in {pacs}."

    # Send the message using pywhatkit
    pywhatkit.sendwhatmsg_instantly(users[doctor]["whatsapp_number"], message_body, 10, True, 2)

    return redirect(url_for('admin_control'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
