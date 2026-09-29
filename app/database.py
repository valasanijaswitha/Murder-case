import sqlite3
from pathlib import Path


TEAM_MIGRATIONS = {
    'solved_puzzles': "TEXT DEFAULT ''",
    'unlocked_evidence': "TEXT DEFAULT 'body,cctv_feed,handwritten_note,smartwatch'",
    'story_briefing_completed': "BOOLEAN DEFAULT 0",
    'theory_notes': "TEXT DEFAULT ''",
    'timeline_discoveries': "TEXT DEFAULT ''",
}


def migrate_database(database_path):
    """Apply additive SQLite migrations without replacing existing data."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        existing_columns = {
            row[1] for row in connection.execute('PRAGMA table_info(team)')
        }
        if not existing_columns:
            return []

        added_columns = []
        for column_name, definition in TEAM_MIGRATIONS.items():
            if column_name not in existing_columns:
                connection.execute(
                    f'ALTER TABLE team ADD COLUMN {column_name} {definition}'
                )
                added_columns.append(column_name)
        return added_columns