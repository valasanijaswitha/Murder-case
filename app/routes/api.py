from flask import Blueprint, request, jsonify, session
from app.models import db, Team, Evidence, ActivityLog
from app.engine.game_engine import GameEngine

api_bp = Blueprint('api', __name__)

@api_bp.route('/timer')
def get_timer():
    remaining = GameEngine.get_remaining_seconds()
    h = remaining // 3600
    m = (remaining % 3600) // 60
    s = remaining % 60
    return jsonify({"remaining": remaining, "formatted": f"{h:02d}:{m:02d}:{s:02d}"})

@api_bp.route('/team/state')
def team_state():
    if 'team_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    team = Team.query.get(session['team_id'])
    if not team:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "score": team.score,
        "ghost_points": team.ghost_points,
        "current_round": team.current_round,
        "solved_puzzles": team.solved_puzzles.split(',') if team.solved_puzzles else [],
        "unlocked_evidence": team.unlocked_evidence.split(',') if team.unlocked_evidence else [],
        "status": team.status
    })

@api_bp.route('/team/evidence/<ev_id>')
def get_evidence(ev_id):
    if 'team_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    team = Team.query.get(session['team_id'])
    unlocked = team.unlocked_evidence.split(',') if team.unlocked_evidence else []
    if ev_id not in unlocked:
        return jsonify({"error": "Locked"}), 403
    ev = Evidence.query.get(ev_id)
    if not ev:
        return jsonify({"error": "Not found"}), 404
    GameEngine.log(team.id, 'EVIDENCE_OPENED', 'EVIDENCE', ev_id)
    db.session.commit()
    return jsonify({"id": ev.id, "name": ev.name, "content": ev.content, "type": ev.type})

@api_bp.route('/team/submit', methods=['POST'])
def submit_puzzle():
    if 'team_id' not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    data = request.json
    result = GameEngine.validate_submission(session['team_id'], data.get('puzzle_id'), data.get('answer', ''))
    return jsonify(result)

@api_bp.route('/team/hint', methods=['POST'])
def use_hint():
    if 'team_id' not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    data = request.json
    result = GameEngine.use_hint(session['team_id'], data.get('puzzle_id'), int(data.get('hint_index', 0)))
    return jsonify(result)

@api_bp.route('/team/final', methods=['POST'])
def final_accusation_api():
    if 'team_id' not in session:
        return jsonify({"success": False}), 401
    data = request.json
    result = GameEngine.grade_final_accusation(
        session['team_id'],
        data.get('who', ''), data.get('how', ''),
        data.get('why', ''), data.get('truth', ''),
        data.get('evidence', [])
    )
    return jsonify(result)

# Admin API
@api_bp.route('/admin/timer/start', methods=['POST'])
def admin_start_timer():
    GameEngine.start_timer()
    return jsonify({"ok": True})

@api_bp.route('/admin/timer/pause', methods=['POST'])
def admin_pause_timer():
    GameEngine.pause_timer()
    return jsonify({"ok": True})

@api_bp.route('/admin/timer/add', methods=['POST'])
def admin_add_time():
    data = request.json
    GameEngine.add_time(int(data.get('seconds', 300)))
    return jsonify({"ok": True})

@api_bp.route('/admin/team/<int:team_id>/round', methods=['POST'])
def admin_force_round(team_id):
    data = request.json
    team = Team.query.get(team_id)
    if team:
        team.current_round = int(data.get('round', team.current_round))
        db.session.commit()
    return jsonify({"ok": True})

@api_bp.route('/admin/team/<int:team_id>/ghost', methods=['POST'])
def admin_grant_ghost(team_id):
    team = Team.query.get(team_id)
    if team:
        team.ghost_points += 1
        db.session.commit()
    return jsonify({"ok": True})

@api_bp.route('/admin/team/<int:team_id>/pause', methods=['POST'])
def admin_pause_team(team_id):
    team = Team.query.get(team_id)
    if team:
        team.status = 'PAUSED' if team.status != 'PAUSED' else 'ACTIVE'
        db.session.commit()
    return jsonify({"ok": True, "status": team.status})

@api_bp.route('/admin/teams')
def admin_teams():
    teams = Team.query.all()
    result = []
    for t in teams:
        result.append({
            "id": t.id, "team_name": t.team_name, "team_code": t.team_code,
            "player1": t.player1_name, "player2": t.player2_name,
            "round": t.current_round, "score": t.score,
            "ghost_points": t.ghost_points, "status": t.status,
            "solved": t.solved_puzzles
        })
    remaining = GameEngine.get_remaining_seconds()
    return jsonify({"teams": result, "timer_remaining": remaining})

@api_bp.route('/admin/logs/<int:team_id>')
def admin_team_logs(team_id):
    logs = ActivityLog.query.filter_by(team_id=team_id).order_by(ActivityLog.timestamp.desc()).limit(50).all()
    return jsonify([{
        "action": l.action, "target": l.target_id,
        "time": l.timestamp.strftime('%H:%M:%S'), "meta": l.metadata_json
    } for l in logs])
