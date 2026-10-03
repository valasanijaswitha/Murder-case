import hmac
import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Team, Admin, ActivityLog
from app.engine.game_engine import GameEngine

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_password:
        return render_template('admin/login.html', error="Admin login is not configured."), 503
    if request.method == 'POST':
        if hmac.compare_digest(request.form.get('password', ''), admin_password):
            session['is_admin'] = True
            session.permanent = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', error="Invalid password.")
    return render_template('admin/login.html')

@admin_bp.route('/')
def dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.all()
    rounds = _ensure_round_configs()
    return render_template('admin/dashboard.html', teams=teams, rounds=rounds)

@admin_bp.route('/teams')
def teams():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.all()
    return render_template('admin/teams.html', teams=teams)

@admin_bp.route('/attendance')
def attendance():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.all()
    return render_template('admin/attendance.html', teams=teams)

@admin_bp.route('/event_control')
def event_control():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    rounds = _ensure_round_configs()
    teams = Team.query.order_by(Team.team_name).all()
    team_round_access = {
        team.id: GameEngine.ensure_team_round_access(team, commit=False)
        for team in teams
    }
    db.session.commit()
    timers = {}
    for r in rounds:
        remaining = GameEngine.get_round_remaining_seconds(r.round_number)
        h, m, s = remaining // 3600, (remaining % 3600) // 60, remaining % 60
        timers[r.round_number] = f"{h:02d}:{m:02d}:{s:02d}"
    active_teams = [team for team in teams if team.status == 'ACTIVE']
    round_counts = {
        round_number: sum(team.current_round == round_number for team in active_teams)
        for round_number in range(1, 5)
    }
    completed_count = sum(team.status == 'FINISHED' for team in teams)
    return render_template(
        'admin/event_control.html', rounds=rounds, timers=timers, teams=teams,
        team_round_access=team_round_access, active_team_count=len(active_teams),
        round_counts=round_counts, completed_count=completed_count
    )

def _ensure_round_configs():
    """Seed default RoundConfig rows if they don't exist yet."""
    from app.models import RoundConfig
    round_configs = RoundConfig.query.order_by(RoundConfig.round_number).all()
    if not round_configs:
        for i, name in [(1, 'CRIME SCENE'), (2, 'DIGITAL TRAIL'), (3, 'PROJECT 9'), (4, 'DEDUCTION')]:
            db.session.add(RoundConfig(round_number=i, name=name, status='LOCKED', duration_minutes=30))
        db.session.commit()
        round_configs = RoundConfig.query.order_by(RoundConfig.round_number).all()
    return round_configs


@admin_bp.route('/rounds')
def rounds():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    round_configs = _ensure_round_configs()
    return render_template('admin/rounds.html', rounds=round_configs)

@admin_bp.route('/puzzles')
def puzzles():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    from app.models import Puzzle, Evidence
    puzzles = Puzzle.query.order_by(Puzzle.round_id).all()
    evidence = Evidence.query.order_by(Evidence.round).all()
    return render_template('admin/puzzles.html', puzzles=puzzles, evidence=evidence)

@admin_bp.route('/hints')
def hints():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.all()
    return render_template('admin/hints.html', teams=teams)

@admin_bp.route('/leaderboard')
def leaderboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    teams = Team.query.order_by(Team.score.desc()).all()
    return render_template('admin/leaderboard.html', teams=teams)

@admin_bp.route('/accusations')
def accusations():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    from app.models import FinalAccusation
    accs = FinalAccusation.query.order_by(FinalAccusation.submitted_at.desc()).all()
    teams = {t.id: t.team_name for t in Team.query.all()}
    return render_template('admin/accusations.html', accusations=accs, teams=teams)

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
