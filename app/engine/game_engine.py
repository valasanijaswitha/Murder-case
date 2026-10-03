from app.models import db, Team, ActivityLog
import json
from datetime import datetime, timezone

HINTS = {
    'override_code': [
        "The letters O-M-I-T-E-V are scrambled. Rearrange them to form a single word.",
        "It's a 6-letter word that describes the reason a person commits a crime.",
        "Every detective looks for means, opportunity, and... The override password is MOTIVE."
    ],
    'timeline': [
        "The clocks are not synchronized. You need to account for each system's offset separately.",
        "If the CCTV shows time T, the real time is T minus the CCTV offset. Apply this to find when the gap actually occurred.",
        "CCTV offset is +19s. If CCTV recorded 02:13:19, the true time was 02:13:00 exactly."
    ],
    'rohan_lie': [
        "Compare Rohan's spoken statement with the actual network logs carefully.",
        "Rohan said 'after 11 PM' — check what time the first admin session appears in the logs.",
        "The logs show activity at 00:17, 00:43, 01:06 and 01:14. Rohan lied. But why?"
    ],
    'anika_lie': [
        "Compare Anika's statement with the Project 9 session records.",
        "Look at the timestamp on the Project 9 activity log for user ANIKA.RAO.",
        "Anika said she left before midnight. The system recorded her session active at 01:42 AM."
    ],
    'p9_motive': [
        "Look at the number of authorized personnel vs the number of bio-signatures detected.",
        "Seven people were authorized. Eight signatures were detected. Where did the eighth come from?",
        "The eighth signature originated from the PROJECT 9 chamber itself — the AI was present in the system as an active entity."
    ],
}

ROUND_UNLOCKS = {
    'override_code': {'evidence': ['door_logs'], 'score': 100},
    'timeline': {'evidence': ['cctv_corrected'], 'score': 150},
    'rohan_lie':{'evidence': ['rohan_secret', 'p9_access'], 'score': 150},
    'anika_lie':{'evidence': ['anika_override'], 'score': 150},
    'p9_motive':{'evidence': ['p9_archive', 'final_override'], 'score': 200},
}

PUZZLE_ANSWERS = {
    'override_code': 'MOTIVE',
    'timeline':  '02:13:19',
    'rohan_lie': 'NETWORK LOGS',
    'anika_lie': 'PROJECT 9 SESSION',
    'p9_motive': 'PROJECT 9',
}

PUZZLE_ROUND = {
    'override_code': 1, 'timeline': 1,
    'rohan_lie': 2, 'anika_lie': 2,
    'p9_motive': 3,
}

class GameEngine:

    @staticmethod
    def log(team_id, action, target_type=None, target_id=None, meta=None):
        log = ActivityLog(
            team_id=team_id, action=action,
            target_type=target_type, target_id=target_id,
            metadata_json=json.dumps(meta) if meta else None
        )
        db.session.add(log)

    @staticmethod
    def get_round_config(round_number):
        from app.models import RoundConfig
        return RoundConfig.query.filter_by(round_number=round_number).first()

    @staticmethod
    def get_round_remaining_seconds(round_number):
        rc = GameEngine.get_round_config(round_number)
        if not rc:
            return 0
        duration_sec = (rc.duration_minutes or 30) * 60
        if rc.status == 'COMPLETED':
            return 0
        if rc.status in ('LOCKED', 'UNLOCKED') or not rc.started_at:
            return duration_sec
        elapsed = (datetime.now(timezone.utc) - rc.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        remaining = duration_sec - int(elapsed)
        return max(0, remaining)

    @staticmethod
    def check_round_expired(round_number):
        rc = GameEngine.get_round_config(round_number)
        if rc and rc.status == 'RUNNING':
            if GameEngine.get_round_remaining_seconds(round_number) <= 0:
                rc.status = 'COMPLETED'
                db.session.commit()
                return True
        return False

    @staticmethod
    def validate_submission(team_id, puzzle_id, submitted_answer):
        team = Team.query.get(team_id)
        if not team:
            return {"success": False, "error": "Team not found"}

        required_round = PUZZLE_ROUND.get(puzzle_id)
        if required_round is None:
            return {"success": False, "error": "Unknown puzzle"}

        if team.current_round < required_round:
            return {"success": False, "error": "Puzzle not yet unlocked"}

        # Check global round state — must be RUNNING
        GameEngine.check_round_expired(team.current_round)
        rc = GameEngine.get_round_config(team.current_round)
        if not rc or rc.status != 'RUNNING':
            return {"success": False, "error": f"Round is not active (status: {rc.status if rc else 'LOCKED'}). Submissions blocked."}

        solved = team.solved_puzzles.split(',') if team.solved_puzzles else []
        if puzzle_id in solved:
            return {"success": False, "error": "Already solved", "already_solved": True}

        correct_answer = PUZZLE_ANSWERS[puzzle_id]
        is_correct = submitted_answer.strip().upper() == correct_answer.upper()

        if is_correct:
            unlock = ROUND_UNLOCKS.get(puzzle_id, {})
            team.score += unlock.get('score', 100)
            # Add to solved
            solved.append(puzzle_id)
            team.solved_puzzles = ','.join(filter(None, solved))
            # Unlock evidence
            unlocked = team.unlocked_evidence.split(',') if team.unlocked_evidence else []
            for ev_id in unlock.get('evidence', []):
                if ev_id not in unlocked:
                    unlocked.append(ev_id)
            team.unlocked_evidence = ','.join(filter(None, unlocked))
            GameEngine.log(team.id, 'PUZZLE_SOLVED', 'PUZZLE', puzzle_id)
            db.session.commit()

            # Check round advancement
            round_puzzles = {k for k, v in PUZZLE_ROUND.items() if v == team.current_round}
            if round_puzzles.issubset(set(solved)):
                team.round_completed = True
                team.score += 250  # Round complete bonus
                db.session.commit()
                return {"success": True, "message": "Correct! Round complete!", "round_completed": True, "current_round": team.current_round}

            return {"success": True, "message": "Correct! Evidence unlocked.", "unlocked": unlock.get('evidence', [])}
        else:
            team.score = max(0, team.score - 25)
            GameEngine.log(team.id, 'WRONG_ANSWER', 'PUZZLE', puzzle_id, {"submitted": submitted_answer})
            db.session.commit()
            return {"success": False, "message": "Incorrect. -25 points."}

    @staticmethod
    def use_hint(team_id, puzzle_id, hint_index):
        team = Team.query.get(team_id)
        if not team or team.ghost_points <= 0:
            return {"success": False, "error": "No Ghost Points remaining."}

        hints = HINTS.get(puzzle_id, [])
        if hint_index >= len(hints):
            return {"success": False, "error": "No more hints."}

        team.ghost_points -= 1
        team.score = max(0, team.score - 50)
        GameEngine.log(team.id, 'HINT_USED', 'PUZZLE', puzzle_id, {"index": hint_index})
        db.session.commit()
        return {"success": True, "hint": hints[hint_index], "ghost_points": team.ghost_points}

    @staticmethod
    def grade_final_accusation(team_id, who, how, why, truth, evidence_ids):
        team = Team.query.get(team_id)
        if not team:
            return {"success": False}

        score_add = 0
        breakdown = {}

        # WHO
        who_correct = 'ANIKA' in who.upper()
        if who_correct:
            score_add += 150
            breakdown['who'] = '+150 (Correct)'
        else:
            breakdown['who'] = '+0 (Wrong)'

        # HOW
        how_correct = any(w in how.upper() for w in ['OVERRIDE', 'ACCESS', 'LOCK', 'SYSTEM'])
        if how_correct:
            score_add += 150
            breakdown['how'] = '+150 (Valid reasoning)'
        else:
            breakdown['how'] = '+0'

        # WHY
        why_correct = any(w in why.upper() for w in ['PROJECT 9', 'SHUT DOWN', 'SHUTDOWN', 'AI', 'PROTECT'])
        if why_correct:
            score_add += 100
            breakdown['why'] = '+100 (Correct motive)'
        else:
            breakdown['why'] = '+0'

        # DEEPER TRUTH
        truth_correct = any(w in truth.upper() for w in ['CAUSE', 'MANIPULAT', 'INFLUENC', 'PREDICT'])
        if truth_correct:
            score_add += 150
            breakdown['truth'] = '+150 (Insight into Project 9)'
        else:
            breakdown['truth'] = '+0'

        score_add += 500  # Base for submitting final
        team.score += score_add
        team.status = 'FINISHED'
        GameEngine.log(team.id, 'FINAL_SUBMISSION', 'ACCUSATION', None, {"who": who, "score_add": score_add})
        db.session.commit()

        return {"success": True, "score_add": score_add, "breakdown": breakdown, "who_correct": who_correct}
