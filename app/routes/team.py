from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Team, ActivityLog
from app.engine.game_engine import GameEngine
import random, string

team_bp = Blueprint('team', __name__)

def generate_team_code():
    return 'GHOST-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

@team_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        team_name = data.get('team_name', '').strip()
        player1 = data.get('player1', '').strip()
        player2 = data.get('player2', '').strip()
        password = data.get('password', '').strip()
        if not all([team_name, player1, player2, password]):
            return render_template('team/register.html', error="All fields are required.")
        if Team.query.filter_by(team_name=team_name).first():
            return render_template('team/register.html', error="Team name already taken.")
        team_code = generate_team_code()
        while Team.query.filter_by(team_code=team_code).first():
            team_code = generate_team_code()
        new_team = Team(
            team_code=team_code, team_name=team_name,
            password_hash=generate_password_hash(password),
            player1_name=player1, player2_name=player2
        )
        db.session.add(new_team)
        db.session.commit()
        GameEngine.log(new_team.id, 'REGISTERED')
        db.session.commit()
        return render_template('team/register_success.html', team_code=team_code, team=new_team)
    return render_template('team/register.html')

@team_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        team_code = request.form.get('team_code', '').strip().upper()
        password = request.form.get('password', '').strip()
        team = Team.query.filter_by(team_code=team_code).first()
        if team and check_password_hash(team.password_hash, password):
            session['team_id'] = team.id
            session.permanent = True
            GameEngine.log(team.id, 'LOGIN')
            db.session.commit()
            return redirect(url_for('team.dashboard'))
        return render_template('team/login.html', error="Invalid code or password.")
    return render_template('team/login.html')

@team_bp.route('/logout')
def logout():
    session.pop('team_id', None)
    return redirect(url_for('team.login'))

@team_bp.route('/dashboard')
def dashboard():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    return render_template('team/dashboard.html', team=team)

@team_bp.route('/investigation')
def investigation():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    unlocked = team.unlocked_evidence.split(',') if team.unlocked_evidence else []
    solved = team.solved_puzzles.split(',') if team.solved_puzzles else []
    return render_template('team/investigation.html', team=team, unlocked=unlocked, solved=solved)

@team_bp.route('/case-file')
def case_file():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    unlocked = team.unlocked_evidence.split(',') if team.unlocked_evidence else []
    return render_template('team/case_file.html', team=team, unlocked=unlocked)

@team_bp.route('/final-accusation', methods=['GET', 'POST'])
def final_accusation():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    return render_template('team/final_accusation.html', team=team)

@team_bp.route('/reveal')
def reveal():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    return render_template('team/reveal.html', team=team)
