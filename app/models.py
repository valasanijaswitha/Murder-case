from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_code = db.Column(db.String(20), unique=True, nullable=False)
    team_name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    player1_name = db.Column(db.String(80), nullable=False)
    player2_name = db.Column(db.String(80), nullable=False)
    current_round = db.Column(db.Integer, default=1)
    score = db.Column(db.Integer, default=0)
    ghost_points = db.Column(db.Integer, default=5)
    status = db.Column(db.String(20), default='ACTIVE')
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Store solved puzzles as comma-separated ids
    solved_puzzles = db.Column(db.Text, default='')
    # Store unlocked evidence as comma-separated ids
    unlocked_evidence = db.Column(db.Text, default='body,cctv_feed,handwritten_note,smartwatch')

class Evidence(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    round = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    score_value = db.Column(db.Integer, default=0)

class Puzzle(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    round_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    answer = db.Column(db.String(200), nullable=True)
    points = db.Column(db.Integer, default=100)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    metadata_json = db.Column(db.Text, nullable=True)

class EventTimer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_start = db.Column(db.DateTime, nullable=True)
    event_duration = db.Column(db.Integer, default=9000)  # 150 min in seconds
    is_paused = db.Column(db.Boolean, default=True)
    paused_remaining = db.Column(db.Integer, default=9000)
