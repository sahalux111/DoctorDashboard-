from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Indian Standard Time (IST) timezone
IST = pytz.timezone('Asia/Kolkata')

# Simulated database
users = {
    'admin': {'password': generate_password_hash('adminpassword'), 'role': 'admin'},
    'SahalTest': {'password': generate_password_hash('1234'), 'role': 'doctor'},
    'DrArun': {'password': generate_password_hash('1234'), 'role': 'doctor'},
    'DrTest': {'password': generate_password_hash('1234'), 'role': 'doctor'},
    'QARadiographer1': {'password': generate_password_hash('1234'), 'role': 'qa_radiographer'},
    'QARadiographer2': {'password': generate_password_hash('1234'), 'role': 'qa_radiographer'}
}

available_doctors = {}
available_qa_radiographers = {}
doctor_breaks = {}
qa_radiographer_breaks = {}

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

    current_time = datetime.now(IST)
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    if session['role'] == 'admin':
        for user_dict, break_dict, user_type in [(available_doctors, doctor_breaks, 'doctor'), (available_qa_radiographers, qa_radiographer_breaks, 'qa_radiographer')]:
            for user, (start_time, end_time) in user_dict.items():
                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST)
                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST)

                if start_time <= current_time <= end_time:
                    available_now[user] = end_time.strftime('%Y-%m-%d %H:%M')
                elif start_time > current_time:
                    upcoming_scheduled[user] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

            for user, break_end in break_dict.items():
                if current_time < break_end:
                    breaks[user] = break_end.strftime('%Y-%m-%d %H:%M')

    else:
        user = session['username']
        user_dict = available_doctors if session['role'] == 'doctor' else available_qa_radiographers
        break_dict = doctor_breaks if session['role'] == 'doctor' else qa_radiographer_breaks

        if user in user_dict:
            start_time, end_time = user_dict[user]
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST)
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST)

            if start_time <= current_time <= end_time:
                available_now[user] = end_time.strftime('%Y-%m-%d %H:%M')
            elif start_time > current_time:
                upcoming_scheduled[user] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

        if user in break_dict:
            break_end = break_dict[user]
            if current_time < break_end:
                breaks[user] = break_end.strftime('%Y-%m-%d %H:%M')

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
    
    user = session['username']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    
    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST)
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST)

    if session['role'] == 'doctor':
        available_doctors[user] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))
    elif session['role'] == 'qa_radiographer':
        available_qa_radiographers[user] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('dashboard'))

@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    user = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = datetime.now(IST) + timedelta(minutes=break_duration)

    if session['role'] == 'doctor':
        doctor_breaks[user] = break_end_time
    elif session['role'] == 'qa_radiographer':
        qa_radiographer_breaks[user] = break_end_time

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

    user = request.form['user']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST)
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST)

    if users[user]['role'] == 'doctor':
        available_doctors[user] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))
    elif users[user]['role'] == 'qa_radiographer':
        available_qa_radiographers[user] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('admin_control'))

@app.route('/update_break', methods=['POST'])
def update_break():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    user = request.form['user']
    break_duration = int(request.form['break_duration'])
    break_end_time = datetime.now(IST) + timedelta(minutes=break_duration)

    if users[user]['role'] == 'doctor':
        doctor_breaks[user] = break_end_time
    elif users[user]['role'] == 'qa_radiographer':
        qa_radiographer_breaks[user] = break_end_time

    return redirect(url_for('admin_control'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


