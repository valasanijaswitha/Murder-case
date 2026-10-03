from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Team, ActivityLog, Evidence
from app.engine.game_engine import GameEngine
import random, string

team_bp = Blueprint('team', __name__)

def generate_team_code():
    return 'GHOST-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def _accessible_evidence_ids(team):
    unlocked = team.unlocked_evidence.split(',') if team.unlocked_evidence else []
    evidence = Evidence.query.filter(Evidence.id.in_(unlocked)).all() if unlocked else []
    accessible = {
        item.id for item in evidence
        if GameEngine.can_access_round(team, item.round)
    }
    return [ev_id for ev_id in unlocked if ev_id in accessible]

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
        GameEngine.ensure_team_round_access(new_team)
        session['team_id'] = new_team.id
        session.permanent = True
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
            session.pop('team_portal_entered', None)
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
    session.pop('team_portal_entered', None)
    return redirect(url_for('team.login'))

@team_bp.route('/dashboard')
def dashboard():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    if not team.story_briefing_completed:
        return redirect(url_for('team.briefing'))
    accesses = GameEngine.ensure_team_round_access(team)
    visible_evidence = _accessible_evidence_ids(team)
    session['team_portal_entered'] = team.id
    return render_template(
        'team/dashboard.html', team=team,
        visible_evidence=visible_evidence,
        round_access={number: access for number, access in accesses.items()},
        round_content_access={
            number: GameEngine.can_access_round(team, number)
            for number in range(1, 5)
        }
    )

@team_bp.route('/briefing')
def briefing():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    return render_template('team/story.html', team=team, is_briefing=True)

@team_bp.route('/briefing/complete', methods=['POST'])
def complete_briefing():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if team:
        team.story_briefing_completed = True
        db.session.commit()
    return redirect(url_for('team.dashboard'))

@team_bp.route('/story')
def story():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    return render_template('team/story.html', team=team, is_briefing=False)

@team_bp.route('/investigation')
def investigation():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    if not team.story_briefing_completed and session.get('team_portal_entered') != team.id:
        return redirect(url_for('team.briefing'))
    GameEngine.ensure_team_round_access(team)

    from app.models import RoundConfig
    rc = RoundConfig.query.filter_by(round_number=team.current_round).first()

    if not GameEngine.can_access_round(team, team.current_round, require_global=False):
        return render_template(
            'team/waiting.html', team=team, rc=rc, status='LOCKED',
            message=f'ROUND {team.current_round} HAS NOT BEEN UNLOCKED FOR YOUR TEAM.'
        )
    
    if team.round_completed or (rc and rc.status == 'COMPLETED'):
        return render_template('team/round_complete.html', team=team, round_number=team.current_round)

    if not rc or rc.status == 'LOCKED':
        return render_template('team/waiting.html', team=team, rc=rc, status='LOCKED')
        
    if rc.status == 'UNLOCKED':
        return render_template('team/waiting.html', team=team, rc=rc, status='UNLOCKED')
        
    # rc.status == 'RUNNING'
    GameEngine.check_round_expired(team.current_round)
    rc = RoundConfig.query.filter_by(round_number=team.current_round).first()
    if rc.status == 'COMPLETED':
        return render_template('team/round_complete.html', team=team, round_number=team.current_round)

    unlocked = _accessible_evidence_ids(team)
    solved = team.solved_puzzles.split(',') if team.solved_puzzles else []
    round_access = {}
    for round_number in range(1, 5):
        rc_round = GameEngine.get_round_config(round_number)
        round_access[round_number] = (
            GameEngine.can_access_round(team, round_number)
            and bool(rc_round and rc_round.status in ('RUNNING', 'COMPLETED'))
        )
    return render_template(
        'team/investigation.html', team=team, unlocked=unlocked, solved=solved,
        round_access=round_access,
        accessible_round_numbers=[
            number for number, is_accessible in round_access.items() if is_accessible
        ]
    )

@team_bp.route('/case-file')
def case_file():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    GameEngine.ensure_team_round_access(team)
    unlocked = _accessible_evidence_ids(team)
    return render_template('team/case_file.html', team=team, unlocked=unlocked)

@team_bp.route('/suspects')
def suspects():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    GameEngine.ensure_team_round_access(team)
    return render_template(
        'team/suspects.html', team=team,
        can_view_round2=GameEngine.can_access_round(team, 2)
    )

@team_bp.route('/timeline')
def timeline():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    GameEngine.ensure_team_round_access(team)
    return render_template(
        'team/timeline.html', team=team,
        can_view_round1=GameEngine.can_access_round(team, 1),
        can_view_round2=GameEngine.can_access_round(team, 2),
        can_view_round3=GameEngine.can_access_round(team, 3)
    )

@team_bp.route('/notes', methods=['GET', 'POST'])
def notes():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    if request.method == 'POST':
        data = request.json
        if data and 'notes' in data:
            team.theory_notes = data['notes']
            db.session.commit()
            return jsonify({'status': 'ok'})
        return jsonify({'status': 'error'})
    return render_template('team/notes.html', team=team)

@team_bp.route('/final-accusation', methods=['GET', 'POST'])
def final_accusation():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    if team.status == 'FINISHED':
        return redirect(url_for('team.reveal'))
    if team.current_round != 4 or not GameEngine.can_access_round(team, 4):
        return redirect(url_for('team.dashboard'))
    rc = GameEngine.get_round_config(4)
    if not rc or rc.status != 'RUNNING':
        return render_template(
            'team/waiting.html', team=team, rc=rc,
            status=rc.status if rc else 'LOCKED'
        )
    return render_template('team/final_accusation.html', team=team)

@team_bp.route('/reveal')
def reveal():
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))
    if team.status != 'FINISHED' or not GameEngine.can_access_round(team, 4):
        return redirect(url_for('team.dashboard'))
    return render_template('team/reveal.html', team=team)

@team_bp.route('/proceed/<int:next_round>', methods=['POST'])
def proceed_to_round(next_round):
    """Player clicks PROCEED after completing a round. Server checks global state."""
    if 'team_id' not in session:
        return redirect(url_for('team.login'))
    team = Team.query.get(session['team_id'])
    if not team:
        return redirect(url_for('team.login'))

    if next_round != team.current_round + 1 or next_round > 4:
        return redirect(url_for('team.investigation'))

    accesses = GameEngine.ensure_team_round_access(team)
    previous = accesses.get(team.current_round)
    if not previous or not previous.completed_at:
        return redirect(url_for('team.investigation'))

    from app.models import RoundConfig
    rc = RoundConfig.query.filter_by(round_number=next_round).first()
    if not GameEngine.can_access_round(team, next_round, require_global=False):
        return render_template('team/waiting.html', team=team, rc=rc, status='LOCKED',
                               message=f'ROUND {next_round} HAS NOT BEEN UNLOCKED FOR YOUR TEAM.')
    if not rc or rc.status not in ('UNLOCKED', 'RUNNING'):
        return render_template(
            'team/waiting.html', team=team, rc=rc,
            status=rc.status if rc else 'LOCKED',
            message=f'ROUND {next_round} IS NOT CURRENTLY AVAILABLE. PLEASE WAIT FOR THE GAME MASTER.'
        )

    team.current_round = next_round
    team.round_completed = False
    team.authorized_round = next_round
    db.session.commit()
    GameEngine.log(team.id, 'PROCEED_TO_ROUND', 'ROUND', str(next_round))
    db.session.commit()

    return redirect(url_for('team.investigation'))
