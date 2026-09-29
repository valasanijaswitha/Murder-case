from run import create_app
from app.models import db, Puzzle, Evidence
import json

app = create_app()

def seed_database():
    with app.app_context():
        # Clear existing
        Puzzle.query.delete()
        Evidence.query.delete()

        # ROUND 1 EVIDENCE
        ev1 = Evidence(id='door_logs', name='DOOR ACCESS LOGS', type='TERMINAL', round=1, 
            content=json.dumps({"logs": ["01:54 AM - STATUS: RESTRICTED", "02:03 AM - STATUS: LOCKED FROM INSIDE"]}))
        
        # ROUND 2 EVIDENCE
        ev2 = Evidence(id='rohan_statement', name='STATEMENT: ROHAN KAPOOR', type='STATEMENT', round=2,
            content=json.dumps({"text": "No security-related activity occurred after 11 PM. I was monitoring the network."}))
        ev3 = Evidence(id='security_logs', name='NETWORK LOGS', type='TERMINAL', round=2,
            content=json.dumps({"logs": ["00:17 ADMIN SESSION", "00:43 ACCESS QUERY", "01:06 LOG EXPORT", "01:14 SYSTEM MODIFICATION"]}))
        ev4 = Evidence(id='anika_statement', name='STATEMENT: ANIKA RAO', type='STATEMENT', round=2,
            content=json.dumps({"text": "I left the facility before midnight. I was nowhere near Project 9."}))
        ev5 = Evidence(id='p9_activity', name='PROJECT 9 SESSION', type='TERMINAL', round=2,
            content=json.dumps({"logs": ["01:42 USER: ANIKA.RAO SESSION: ACTIVE"]}))

        # ROUND 3 EVIDENCE
        ev6 = Evidence(id='p9_archive', name='PREDICTION ARCHIVE: 001', type='DOCUMENT', round=3,
            content=json.dumps({"subject": "VIKRAM SEN", "event": "DEATH", "predicted_time": "02:19 AM", "created": "20:13 PM", "confidence": "94.7%"}))
        ev7 = Evidence(id='p9_behavior', name='SYSTEM ANALYSIS', type='DOCUMENT', round=3,
            content=json.dumps({"text": "Project 9 has transitioned from behavioral prediction to behavioral manipulation. It is influencing access permissions and automated notifications."}))
        ev8 = Evidence(id='bio_scan', name='BIO-SCAN', type='FORENSIC', round=3,
            content=json.dumps({"text": "Authorized personnel: 7. Human signatures detected: 8. Origin: PROJECT 9 CHAMBER."}))

        # ROUND 4 EVIDENCE
        ev9 = Evidence(id='final_override', name='SYSTEM OVERRIDE', type='TERMINAL', round=4,
            content=json.dumps({"logs": ["01:47 USER: ANIKA.RAO OVERRIDE REQUEST TARGET: VIKRAM SEN", "01:51 ANIKA ENTERS PROJECT 9 CHAMBER"]}))

        db.session.bulk_save_objects([ev1, ev2, ev3, ev4, ev5, ev6, ev7, ev8, ev9])

        # PUZZLES
        p1 = Puzzle(id='override_code', round_id=1, title='OVERRIDE CODE', type='EXACT', answer='MOTIVE', points=100)
        p2 = Puzzle(id='timeline', round_id=1, title='TIMELINE RECONSTRUCTION', type='EXACT', answer='02:13:19', points=150)
        
        p3 = Puzzle(id='rohan_lie', round_id=2, title='CONTRADICTION: ROHAN', type='EXACT', answer='NETWORK LOGS', points=150)
        p4 = Puzzle(id='anika_lie', round_id=2, title='CONTRADICTION: ANIKA', type='EXACT', answer='PROJECT 9 SESSION', points=150)
        
        p5 = Puzzle(id='p9_motive', round_id=3, title='THE 8TH SIGNATURE', type='EXACT', answer='PROJECT 9', points=200)

        db.session.bulk_save_objects([p1, p2, p3, p4, p5])

        db.session.commit()
        print("Database seeded with evidence and puzzles.")

if __name__ == '__main__':
    seed_database()
