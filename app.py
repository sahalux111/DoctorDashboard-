from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Updated simulated database with new passwords
users = {
    'admin': {'password': generate_password_hash('adminpassword'), 'role': 'admin'},
    'drmonika': {'password': generate_password_hash('drmonika321'), 'role': 'doctor'},
    'dramit': {'password': generate_password_hash('dramit321'), 'role': 'doctor'},
    'drshashank': {'password': generate_password_hash('drshashank321'), 'role': 'doctor'},
    'drronak': {'password': generate_password_hash('drronak321'), 'role': 'doctor'},
    'dranthony': {'password': generate_password_hash('dranthony321'), 'role': 'doctor'},
    'droguntade': {'password': generate_password_hash('droguntade321'), 'role': 'doctor'},
    'drsmitha': {'password': generate_password_hash('drsmitha321'), 'role': 'doctor'},
    'drnikita': {'password': generate_password_hash('drnikita321'), 'role': 'doctor'},
    'drkarim': {'password': generate_password_hash('drkarim321'), 'role': 'doctor'},
    'drfakhri': {'password': generate_password_hash('drfakhri321'), 'role': 'doctor'},
    'imugilteam': {'password': generate_password_hash('imugilteam321'), 'role': 'doctor'},
    'drnamitha': {'password': generate_password_hash('drnamitha321'), 'role': 'doctor'},
    'drsachin': {'password': generate_password_hash('drsachin321'), 'role': 'doctor'},
    'drvivek': {'password': generate_password_hash('drvivek321'), 'role': 'doctor'},
    'drraj': {'password': generate_password_hash('drraj321'), 'role': 'doctor'},
    'rdlteam': {'password': generate_password_hash('rdlteam321'), 'role': 'doctor'},
    'ishateam': {'password': generate_password_hash('ishateam321'), 'role': 'doctor'},
    'drdeepak': {'password': generate_password_hash('drdeepak321'), 'role': 'doctor'},
    'drsurendar': {'password': generate_password_hash('drsurendar321'), 'role': 'doctor'},
    'qa1': {'password': generate_password_hash('password4'), 'role': 'qa'},  # Added QA users
    'qa2': {'password': generate_password_hash('password5'), 'role': 'qa'}
}

available_doctors = {}
doctor_breaks = {}

# Define IST offset
IST_OFFSET = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST_OFFSET)

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

    current_time = get_ist_now()
    available_now = {}
    upcoming_scheduled = {}
    breaks = {}

    if session['role'] in ['admin', 'qa']:
        # Admins and QA users can see all doctors' availability and breaks
        for doctor, (start_time, end_time) in available_doctors.items():
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)

            if start_time <= current_time <= end_time:
                if doctor not in doctor_breaks or current_time > doctor_breaks[doctor]:
                    available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
            elif start_time > current_time:
                upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))
        
        for doctor, break_end in doctor_breaks.items():
            if current_time < break_end:
                breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

    else:
        # Doctors can only see their own availability and breaks
        doctor = session['username']
        if doctor in available_doctors:
            start_time, end_time = available_doctors[doctor]
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)

            if start_time <= current_time <= end_time:
                if doctor not in doctor_breaks or current_time > doctor_breaks[doctor]:
                    available_now[doctor] = end_time.strftime('%Y-%m-%d %H:%M')
            elif start_time > current_time:
                upcoming_scheduled[doctor] = (start_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M'))

        if doctor in doctor_breaks:
            break_end = doctor_breaks[doctor]
            if current_time < break_end:
                breaks[doctor] = break_end.strftime('%Y-%m-%d %H:%M')

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
    
    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)

    available_doctors[doctor] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('dashboard'))

@app.route('/take_break', methods=['POST'])
def take_break():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    doctor = session['username']
    break_duration = int(request.form['break_duration'])
    break_end_time = get_ist_now() + timedelta(minutes=break_duration)

    doctor_breaks[doctor] = break_end_time

    return redirect(url_for('dashboard'))

@app.route('/admin_control')
def admin_control():
    if 'username' not in session or session['role'] not in ['admin', 'qa']:
        return redirect(url_for('index'))

    return render_template('admin_control.html', users=users, available_doctors=available_doctors, doctor_breaks=doctor_breaks)

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    if 'username' not in session or session['role'] not in ['admin', 'qa']:
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    
    availability_start = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)
    availability_end = datetime.strptime(f'{start_date} {end_time}', '%Y-%m-%d %H:%M').replace(tzinfo=IST_OFFSET)

    available_doctors[doctor] = (availability_start.strftime('%Y-%m-%d %H:%M'), availability_end.strftime('%Y-%m-%d %H:%M'))

    return redirect(url_for('admin_control'))

@app.route('/update_break', methods=['POST'])
def update_break():
    if 'username' not in session or session['role'] not in ['admin', 'qa']:
        return redirect(url_for('index'))

    doctor = request.form['doctor']
    break_duration = int(request.form['break_duration'])
    break_end_time = get_ist_now() + timedelta(minutes=break_duration)

    doctor_breaks[doctor] = break_end_time

    return redirect(url_for('admin_control'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

