from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Team, Admin, ActivityLog, EventTimer
from app.engine.game_engine import GameEngine

admin_bp = Blueprint('admin', __name__)

ADMIN_PASSWORD = 'helix-admin-2026'

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', error="Invalid password.")
    return render_template('admin/login.html')

@admin_bp.route('/')
def dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.all()
    timer = GameEngine.get_timer()
    remaining = GameEngine.get_remaining_seconds()
    h, m, s = remaining // 3600, (remaining % 3600) // 60, remaining % 60
    return render_template('admin/dashboard.html', teams=teams, timer=timer,
                           time_str=f"{h:02d}:{m:02d}:{s:02d}")

@admin_bp.route('/leaderboard')
def leaderboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.order_by(Team.score.desc()).all()
    return render_template('admin/leaderboard.html', teams=teams)

@admin_bp.route('/activity')
def activity():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    teams = {t.id: t.team_name for t in Team.query.all()}
    return render_template('admin/activity.html', logs=logs, teams=teams)

@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))
