from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import json
from datetime import datetime
import uuid
import logging

app = Flask(__name__)

# Database initialization
DATABASE = 'esmailtimes.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
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
                room_available TEXT NOT NULL DEFAULT 'Unknown', --default value set here
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
                lecturer_name TEXT NOT NULL,
                unit_name TEXT NOT NULL,
                day TEXT NOT NULL,
                times TEXT NOT NULL,
                request_id INTEGER NOT NULL,
                slots TEXT,
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

@app.route('/select-role', methods=['GET', 'POST'])
def select_role():
    if request.method == 'POST':
        role = request.form.get('role')
        user_id = request.form.get('user_id')  # User ID for Lecturer or Student

        if role == 'lecturer':
            return redirect(f'/dashboard/lecturer/{user_id}')
        elif role == 'timetabler':
            return redirect('/dashboard/timetabler')
        elif role == 'student':
            return redirect(f'/dashboard/student/{user_id}')
        else:
            return "Invalid role selected", 400

    return render_template('select_role.html')

@app.route('/request/create', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        lecturer_id = request.form.get('lecturer_id')
        lecturer_name = request.form.get('lecturer_name')
        course_id = request.form.get('course_id')  # Retrieve course_id from the form
        room_available = request.form.get('room_available')
        unit_name = request.form.get('unit_name')
        student_count = request.form.get('student_count')
        preferred_days = ','.join(request.form.getlist('preferred_days'))
        preferred_times = ','.join(request.form.getlist('preferred_times'))
        additional_notes = request.form.get('additional_notes', '')

        # Validate that course_id is provided
        if not course_id:
            return "Course ID is required", 400

        request_id = str(uuid.uuid4())[:8]
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO timetable_requests (id, lecturer_id, lecturer_name, course_id, room_available, unit_name, student_count, preferred_days, preferred_times, additional_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (request_id, lecturer_id, lecturer_name, course_id, room_available, unit_name, student_count, preferred_days, preferred_times, additional_notes))
            conn.commit()

        return redirect(f'/dashboard/lecturer/{lecturer_id}')

    return render_template('create_request.html')

@app.route('/dashboard/lecturer/<lecturer_id>')
def lecturer_dashboard(lecturer_id):
    with get_db_connection() as conn:
        requests = conn.execute('''
            SELECT * FROM timetable_requests WHERE lecturer_id = ?
        ''', (lecturer_id,)).fetchall()
    return render_template('lecturer_dashboard.html', requests=requests)

@app.route('/dashboard/timetabler')
def timetabler_dashboard():
    with get_db_connection() as conn:
        #requests = conn.execute('SELECT * FROM timetable_requests').fetchall()
        #requests = conn.execute('''
        #    SELECT r.*, u.name as lecturer_name, c.name as course_name
        #    FROM timetable_requests r
        #    JOIN users u ON r.lecturer_id = u.id
        #    JOIN courses c ON r.course_id = c.id
        #''').fetchall()
        requests = conn.execute('''
            SELECT r.id, r.lecturer_id, c.course_id, r.unit_name
            FROM timetable_requests r
            LEFT JOIN courses c ON r.course_id = c.course_id
            WHERE r.status = 'pending'
        ''').fetchall()
        timetables = conn.execute('SELECT * FROM timetables').fetchall()

    # Parse slots JSON for each timetable
    parsed_timetables = []
    for timetable in timetables:
        slots = timetable['slots']
        try:
            import json
            # Ensure slots is a valid JSON string
            slots_parsed = json.loads(slots) if isinstance(slots, str) else []
        except (json.JSONDecodeError, TypeError):
            slots_parsed = []  # Handle invalid JSON gracefully

        parsed_timetables.append({
            "id": timetable["id"],
            "request_id": timetable["request_id"],
            "slots": slots_parsed,
            "status": timetable["status"],
            "created_at": timetable["created_at"]
        })

    return render_template('timetabler_dashboard.html', requests=requests, timetables=parsed_timetables)

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

@app.view('/dashboard/timetabler/view/<int:id>')
def view_request(id):
    request_details = get_request_details(id)
    return render_template('request_details.html', request=request_details)

@app.route('/dashboard/student/<student_id>')
def student_dashboard(student_id):
    with get_db_connection() as conn:
        timetables = conn.execute('''
            SELECT t.* FROM timetables t
            JOIN timetable_requests r ON t.request_id = r.id
            JOIN enrollments e ON r.course_id = e.course_id
            WHERE e.user_id = ?
        ''', (student_id,)).fetchall()
    return render_template('student_dashboard.html', timetables=timetables)

@app.route('/timetable/create/<request_id>', methods=['POST'])
def create_timetable(request_id):
    data = request.get_json(force=True)

    lecturer_name = data.get('lecturer_name')
    student_count = data.get('student_count')
    slots = data.get('slots')

    if not lecturer_name or not isinstance(student_count, int):
        return jsonify({"error": "Lecturer name and valid student count required."}), 400
    if not slots or not isinstance(slots, list):
        return jsonify({"error": "Slots should be a list of objects."}), 400

    slots_json = json.dumps(slots)
    timetable_id = str(uuid.uuid4())[:8]

    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO timetables (id, request_id, lecturer_name, student_count, slots, status)
            VALUES (?, ?, ?, ?, ?, 'finalized')
        ''', (timetable_id, request_id, lecturer_name, student_count, slots_json))
        conn.commit()

    return jsonify({"message": "Timetable created", "timetable_id": timetable_id})


#@app.route('/timetable/create/<request_id>', methods=['POST'])
#def create_timetable(request_id):
#    # Check if the request is JSON
#    if request.is_json:
#        data = request.json
#    else:
#        # Fallback to form data if JSON is not provided
#        data = request.form
#
#    #Retrievr lecturer name from the data
#    lecturer_name = data.get('lecturer_name')
#    if not lecturer_name:
#        return jsonify({"error": "Lecturer name is required. Please provide valid name in json format."}), 400
#    
#    #Retrieve student count from the data
#    student_count = data.get('student_count')
#    if not student_count:
#        return jsonify({"error": "Student count is needed. Please provide a valid number."}), 400
#
#    # Retrieve the slots from the data
#    slots = data.get('slots')  # JSON string of timetable slots
#    if not slots:
#        return jsonify({"error": "Slots are required. Please provide valid slots in JSON format."}), 400
#
#    try:
#        # Validate that slots is a valid JSON string
#        import json
#        slots_parsed = json.loads(slots)  # Parse the JSON string
#        if not isinstance(slots_parsed, list):  # Ensure it's a list
#            raise ValueError("Slots must be a list of objects.")
#        slots = json.dumps(slots_parsed)  # Ensure it's stored as a JSON string
#    except (json.JSONDecodeError, ValueError) as e:
#        return jsonify({"error": f"Invalid JSON format for slots: {str(e)}"}), 400
#
#    timetable_id = str(uuid.uuid4())[:8]
#
#    with get_db_connection() as conn:
#        conn.execute('''
#            INSERT INTO timetables (id, lecturer_name, request_id, slots, student_count, status)
#            VALUES (?, ?, ?, ?, ?, 'finalized')
#        ''', (timetable_id, lecturer_name, request_id, student_count, slots))
#        conn.commit()
#
#    return jsonify({"message": "Timetable created successfully", "timetable_id": timetable_id})

@app.route('/timetable/update/<timetable_id>', methods=['POST'])
def update_timetable(timetable_id):
    if not request.is_json:
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

    return jsonify({"success": True, "message": "Timetable updated successfully."})

@app.route('/timetable/approve/<request_id>', methods=['POST'])
def approve_request(request_id):
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE timetable_requests
            SET status = 'approved'
            WHERE id = ?
        ''', (request_id,))
        conn.commit()
    return redirect('/dashboard/timetabler')

@app.route('/timetable/reject/<request_id>', methods=['POST'])
def reject_request(request_id):
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE timetable_requests
            SET status = 'rejected'
            WHERE id = ?
        ''', (request_id,))
        conn.commit()
    return redirect('/dashboard/timetabler')

@app.route('/timetable/delete/<request_id>', methods=['POST'])
def delete_request(request_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM timetables WHERE request_id = ?', (request_id,))
        conn.execute('DELETE FROM timetable_requests WHERE id = ?', (request_id,))
        conn.commit()
    return redirect('/dashboard/timetabler')

#@app.route('/timetable/delete/<request_id>', methods=['POST'])
#def delete_request(request_id):
#    with get_db_connection() as conn:
#        conn.execute('''
#            DELETE FROM timetable_requests
#            WHERE id = ?
#        ''', (request_id,))
#        conn.commit()
#    return redirect('/dashboard/timetabler')

@app.route('/dashboard/timetabler/view/<request_id>')
def view_lecturer_request(request_id):
    with get_db_connection() as conn:
        # Fetch the lecturer's request details
        #request = conn.execute('''
        #    SELECT lecturer_id, lecturer_name, course, unit_name, room_availability, number_of_students,
        #           preferred_days, preferred_times, additional_notes, status
        #    FROM timetable_requests
        #    WHERE id = ?
        #''', (request_id,)).fetchone()
        request = conn.execute('''
            SELECT r.id, r.lecturer_id, course.course_id, r.unit_name
            FROM timetable_requests r
            LEFT JOIN courses course ON r.course_id = course.course_id
            WHERE r.status = 'pending'
        ''').fetchall()


    if not request:
        return "Request not found", 404

    return render_template('view_lecturer_request.html', request=request)

if __name__ == '__main__':
    app.run(debug=False)  # Disable debug mode