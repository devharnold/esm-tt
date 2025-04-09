from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import json
from datetime import datetime
import uuid
import logging

app = Flask(__name__)

# Database initialization
DATABASE = 'projo.db'

def get_db_connection():
    conn = sqlite3.connect('projo.db')  # Ensure this matches your database file
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


# Create tables if they don't exist
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                course_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                user_id INTEGER,
                course_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(course_id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS timetable_requests (
                id TEXT PRIMARY KEY,
                lecturer_id INTEGER NOT NULL,
                lecturer_name STRING NOT NULL,
                course_id INTEGER,
                unit_name TEXT NOT NULL,
                room_available TEXT NOT NULL DEFAULT 'Unknown',
                student_count INTEGER NOT NULL,
                preferred_days TEXT,
                preferred_times TEXT,
                additional_notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                timetable_id STRING,
                FOREIGN KEY(lecturer_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS timetables (
                id TEXT PRIMARY KEY,
                lecturer_id TEXT NOT NULL,
                unit_name TEXT NOT NULL,
                lecturer_name TEXT NOT NULL,
                request_id TEXT NOT NULL,
                day TEXT,
                time TEXT,
                room TEXT NOT NULL DEFAULT 'Unknown',
                student_count INTEGER NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return redirect('/select-role')

#Route to facilitate the `select-role` function, it fetches then posts data
@app.route('/select-role', methods=['GET', 'POST'])
def select_role():
    if request.method == 'POST':
        role = request.form.get('role')
        user_id = request.form.get('user_id')  # User ID for Lecturer or Student

        if role == 'lecturer':
            return redirect(f'/dashboard/lecturer/{user_id}') # redirects to the lecturer dashboard
        elif role == 'timetabler':
            return redirect('/dashboard/timetabler') #redirects to the timetabler dashboard
        elif role == 'student':
            return redirect(f'/dashboard/student/{user_id}') # redirects to the student dashboard
        else:
            return "Invalid role selected", 400

    return render_template('select_role.html')

#API Route to handle timetable creation request
@app.route('/request/create', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        # Retrieve form data
        lecturer_id = request.form.get('lecturer_id')
        lecturer_name = request.form.get('lecturer_name')
        room_available = request.form.get('room_available')
        unit_name = request.form.get('unit_name')
        student_count = request.form.get('student_count')
        preferred_days = ','.join(request.form.getlist('preferred_days'))
        preferred_times = ','.join(request.form.getlist('preferred_times'))
        additional_notes = request.form.get('additional_notes', '')

        # Validate that all required fields are provided
        if not lecturer_id or not lecturer_name or not unit_name:
            return "All fields are required", 400

        # Generate a unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Insert the request into the timetable_requests table
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO timetable_requests (id, lecturer_id, lecturer_name, room_available, unit_name, student_count, preferred_days, preferred_times, additional_notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (request_id, lecturer_id, lecturer_name, room_available, unit_name, student_count, preferred_days, preferred_times, additional_notes))
            conn.commit()

        return redirect(f'/dashboard/lecturer/{lecturer_id}')

    #renders the create_request page
    return render_template('create_request.html')


# API route to redirect to the lecturer dashboard, it will fetch all details including the timetable
@app.route('/dashboard/lecturer/<lecturer_id>')
def lecturer_dashboard(lecturer_id):
    with get_db_connection() as conn:
        # Fetch all timetables associated with the lecturer
        timetables = conn.execute('''
            SELECT id, unit_name, day, time, room, status
            FROM timetables
            WHERE lecturer_id = ? AND status IN ('sent', 'shared', 'draft')
        ''', (lecturer_id,)).fetchall()

        # Fetch all requests made by the lecturer
        requests = conn.execute('''
            SELECT id, unit_name, status, created_at
            FROM timetable_requests
            WHERE lecturer_id = ?
        ''', (lecturer_id,)).fetchall()

    #renders the frontend template
    return render_template('lecturer_dashboard.html', timetables=timetables, requests=requests)

#API route to redirect to the timetabler's dashboard
@app.route('/dashboard/timetabler')
def timetabler_dashboard():
    with get_db_connection() as conn:
        # Fetch all requests
        requests = conn.execute('''
            SELECT id, lecturer_name, unit_name, status
            FROM timetable_requests
        ''').fetchall()

        # Fetch all timetables
        timetables = conn.execute('''
            SELECT id, lecturer_name, unit_name, day, time, room, status
            FROM timetables
        ''').fetchall()

    #renders the timetabler dashboard's page
    return render_template('timetabler_dashboard.html', requests=requests, timetables=timetables)

@app.route('/timetables/public')
def view_all_timetables():
    with get_db_connection() as conn:
        timetables = conn.execute('''
            SELECT t.*, u.name AS lecturer_name, c.name AS course_name, r.unit_name
            FROM timetables t
            JOIN timetable_requests r ON t.request_id = r.id
            JOIN users u ON r.lecturer_id = u.id
            JOIN courses c ON r.course_id = c.id
            WHERE t.status = 'finalized'
        ''').fetchall()

        parsed_timetables = []
        import json
        for timetable in timetables:
            try:
                slots_parsed = json.loads(timetable['slots'])
            except:
                slots_parsed = []
            parsed_timetables.append({
                "timetable_id": timetable['id'],
                "lecturer_name": timetable['lecturer_name'],
                "unit_name": timetable['unit_name'],
                "lecturer_name": timetable['lecturer_name'],
                "course_name": timetable['course_name'],
                "slots": slots_parsed
            })

    return render_template('public_timetables.html', timetables=parsed_timetables)

@app.route('/dashboard/timetabler/search', methods=['GET'])
def search_lecturer_requests():
    lecturer_id = request.args.get('lecturer_id')  # Get the Lecturer User ID from the form

    if not lecturer_id:
        return redirect('/dashboard/timetabler')  # Redirect back if no ID is provided

    with get_db_connection() as conn:
        # Fetch requests made by the specified lecturer
        requests = conn.execute('''
            SELECT * FROM timetable_requests
            WHERE lecturer_id = ?
        ''', (lecturer_id,)).fetchall()

    return render_template('timetabler_dashboard.html', requests=requests, lecturer_id=lecturer_id)

@app.route('/dashboard/student/<student_id>')
def student_dashboard(student_id):
    with get_db_connection() as conn:
        # Fetch all timetables with status 'shared'
        timetables = conn.execute('''
            SELECT id, unit_name, day, time, room, status
            FROM timetables
            WHERE status = 'shared'
        ''').fetchall()

    # Render the student dashboard with shared timetables
    return render_template('student_dashboard.html', timetables=timetables)

@app.route('/timetable/create/<request_id>', methods=['GET', 'POST'])
def create_timetable(request_id):
    with get_db_connection() as conn:
        # Fetch the request details to pre-fill the timetable form
        lecturer_request = conn.execute('''
            SELECT id, lecturer_id, lecturer_name, unit_name, room_available, student_count,
                   preferred_days, preferred_times, additional_notes
            FROM timetable_requests
            WHERE id = ?
        ''', (request_id,)).fetchone()

        if not lecturer_request:
            return "Request not found", 404

        if request.method == 'POST':  # Handle form submission
            # Retrieve form data for the timetable
            day = request.form.get('day')
            time = request.form.get('time')
            room = request.form.get('room')

            # Generate a unique timetable ID
            timetable_id = str(uuid.uuid4())[:8]

            # Insert the timetable into the database
            conn.execute('''
                INSERT INTO timetables (id, lecturer_id, lecturer_name, unit_name, request_id, day, time, room, student_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timetable_id, lecturer_request['lecturer_id'], lecturer_request['lecturer_name'],
                  lecturer_request['unit_name'], request_id, day, time, room, lecturer_request['student_count']))
            conn.commit()

            #render the timetabler's dashboard
            return redirect('/dashboard/timetabler')
        
    #render the create timetable page
    return render_template('create_timetable.html', request=lecturer_request)

# API route to render the update button, perform actions on it
@app.route('/timetable/update/<timetable_id>', methods=['POST'])
def update_timetable(timetable_id):
    if not request.is_json: #first fetch details in json format
        return jsonify({"success": False, "error": "Invalid request format. JSON expected."}), 400

    data = request.json
    slots = data.get('slots')

    if not slots or not isinstance(slots, list):
        return jsonify({"success": False, "error": "Invalid slots format. A list of slots is required."}), 400

    try:
        import json
        slots_json = json.dumps(slots)  # Convert slots back to JSON string
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Failed to serialize slots to JSON."}), 400

    with get_db_connection() as conn:
        conn.execute('''
            UPDATE timetables
            SET slots = ?, modified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (slots_json, timetable_id))
        conn.commit()

    # return a success message
    return jsonify({"success": True, "message": "Timetable updated successfully."})

#API route to render the approve button
@app.route('/request/approve/<request_id>', methods=['POST'])
def approve_request(request_id):
    with get_db_connection() as conn:
        # Update the status of the request to 'approved'
        conn.execute('''
            UPDATE timetable_requests
            SET status = 'approved'
            WHERE id = ?
        ''', (request_id,))
        conn.commit()

    # Redirect back to the Timetabler Dashboard
    return redirect('/dashboard/timetabler')

#API route to render the reject request button
@app.route('/request/reject/<request_id>', methods=['POST'])
def reject_request(request_id):
    with get_db_connection() as conn:
        # Update the status of the request to 'rejected'
        conn.execute('''
            UPDATE timetable_requests
            SET status = 'rejected'
            WHERE id = ?
        ''', (request_id,))
        conn.commit()

    #redirects to the timetabler dashboard
    return redirect('/dashboard/timetabler')

#API route to render the delete button
@app.route('/timetable/delete/<request_id>', methods=['POST'])
def delete_request(request_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM timetables WHERE request_id = ?', (request_id,))
        conn.execute('DELETE FROM timetable_requests WHERE id = ?', (request_id,))
        conn.commit()
    #redirects to the timetabler dashboard
    return redirect('/dashboard/timetabler')

#API route to view the lecturer's requests within the timetabler's dashboard
@app.route('/dashboard/timetabler/view/<request_id>')
def view_lecturer_request(request_id):
    with get_db_connection() as conn:
        # Fetch the specific request details
        request = conn.execute('''
            SELECT id, lecturer_id, lecturer_name, unit_name, room_available, student_count,
                   preferred_days, preferred_times, additional_notes, status, created_at
            FROM timetable_requests
            WHERE id = ?
        ''', (request_id,)).fetchone()

    if not request:
        return "Request not found", 404

    #redirect to the lecturer's request page
    return render_template('view_lecturer_request.html', request=request)

@app.route('/timetables')
def view_timetables():
    with get_db_connection() as conn:
        timetables = conn.execute('''
            SELECT * FROM timetables
        ''').fetchall()

    #redirects to the timetable views page
    return render_template('view_timetables.html', timetables=timetables)

#API route to render the send button
@app.route('/timetable/send/<timetable_id>', methods=['POST'])
def send_timetable(timetable_id):
    with get_db_connection() as conn:
        # Update the timetable status to 'sent'
        conn.execute('''
            UPDATE timetables
            SET status = 'sent'
            WHERE id = ?
        ''', (timetable_id,))
        conn.commit()

    #redirects to the timetabler's dashboard
    return redirect('/dashboard/timetabler')

# API route to render the share page
@app.route('/timetable/share/<timetable_id>', methods=['POST'])
def share_timetable(timetable_id):
    with get_db_connection() as conn:
        # Fetch the lecturer_id associated with the timetable
        timetable = conn.execute('''
            SELECT lecturer_id
            FROM timetables
            WHERE id = ?
        ''', (timetable_id,)).fetchone()

        if not timetable:
            return "Timetable not found", 404

        lecturer_id = timetable['lecturer_id']

        # Update the timetable status to 'shared'
        conn.execute('''
            UPDATE timetables
            SET status = 'shared'
            WHERE id = ?
        ''', (timetable_id,))
        conn.commit()

    # Redirect back to the lecturer's dashboard
    return redirect(f'/dashboard/lecturer/{lecturer_id}')

if __name__ == '__main__':
    app.run(debug=True)