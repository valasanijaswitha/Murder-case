import os
import json
from run import create_app
from app.models import db, Team
from app.engine.game_engine import GameEngine

app = create_app()

with app.app_context():
    # 1. Setup a dummy team
    team_code = 'TEST_TEAM'
    team = Team.query.filter_by(team_code=team_code).first()
    if not team:
        team = Team(
            team_code=team_code,
            team_name='The Testers',
            password_hash='dummy',
            player1_name='Alice',
            player2_name='Bob',
            current_round=1,
            unlocked_evidence='body,cctv_feed,handwritten_note,smartwatch'
        )
        db.session.add(team)
        db.session.commit()
    else:
        # Reset team
        team.current_round = 1
        team.solved_puzzles = ''
        team.unlocked_evidence = 'body,cctv_feed,handwritten_note,smartwatch'
        team.score = 0
        db.session.commit()
        
    print(f"Testing for Team: {team.team_name} (ID: {team.id})")
    
    # 2. Round 1 Puzzles
    print("\n--- ROUND 1 ---")
    res1 = GameEngine.validate_submission(team.id, 'override_code', 'MOTIVE')
    print(f"Override Code submission: {res1}")
    
    res2 = GameEngine.validate_submission(team.id, 'timeline', '02:13:19')
    print(f"Timeline submission: {res2}")
    
    db.session.refresh(team)
    print(f"Current Round after R1 puzzles: {team.current_round}")
    
    # 3. Round 2 Puzzles
    print("\n--- ROUND 2 ---")
    res3 = GameEngine.validate_submission(team.id, 'rohan_lie', 'NETWORK LOGS')
    print(f"Rohan Lie submission: {res3}")
    
    res4 = GameEngine.validate_submission(team.id, 'anika_lie', 'PROJECT 9 SESSION')
    print(f"Anika Lie submission: {res4}")
    
    db.session.refresh(team)
    print(f"Current Round after R2 puzzles: {team.current_round}")
    
    # 4. Round 3 Puzzles
    print("\n--- ROUND 3 ---")
    res5 = GameEngine.validate_submission(team.id, 'p9_motive', 'PROJECT 9')
    print(f"P9 Motive submission: {res5}")
    
    db.session.refresh(team)
    print(f"Current Round after R3 puzzles: {team.current_round}")
    print(f"Unlocked Evidence: {team.unlocked_evidence}")
    
    # 5. Final Accusation
    print("\n--- FINAL ACCUSATION ---")
    if team.current_round >= 4:
        res6 = GameEngine.grade_final_accusation(
            team.id, 
            who='Anika Rao', 
            how='System override and lockdown', 
            why='To protect Project 9 from shutdown', 
            truth='Project 9 was manipulating outcomes', 
            evidence_ids=['Prediction Archive 001', 'Final Override Log']
        )
        print(f"Final Accusation submission: {res6}")
        db.session.refresh(team)
        print(f"Final Status: {team.status}, Final Score: {team.score}")
    else:
        print("Round 4 not reached. Final Accusation not available.")
