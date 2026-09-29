import sqlite3
import os

db_path = os.path.join('instance', 'murder_case.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("UPDATE puzzle SET answer = 'MOTIVE' WHERE id = 'override_code'")
conn.commit()
conn.close()
print("Updated successfully")
