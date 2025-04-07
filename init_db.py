from app import app, db, init_db
import uuid
from datetime import datetime

class TimetableRequest(db.Model):
    id = db.Column(db.String(8), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    lecturer_id = db.Column(db.String(8), nullable=False)
    lecturer_name = db.Column(db.String(50), nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    room_available = db.Column(db.String(50), nullable=False)
    course_id = db.Column(db.Integer(50), nullable=False)
    student_count = db.Column(db.Integer, nullable=False)
    preferred_days = db.COlumn(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    init_db()
    print("Database initialized successfully!")