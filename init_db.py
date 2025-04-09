from app import app, db, init_db
import uuid
from datetime import datetime

#Timetable request model
class TimetableRequest(db.Model):
    id = db.Column(db.String(8), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    lecturer_id = db.Column(db.String(8), nullable=False)
    lecturer_name = db.Column(db.String(50), nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    room_available = db.Column(db.String(50), nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    student_count = db.Column(db.Integer, nullable=False)
    preferred_days = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

from app import app, init_db

# Initialize the database
init_db()