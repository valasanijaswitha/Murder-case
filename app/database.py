import sqlite3
from pathlib import Path


TEAM_MIGRATIONS = {
    'solved_puzzles': "TEXT DEFAULT ''",
    'unlocked_evidence': "TEXT DEFAULT 'body,cctv_feed,handwritten_note,smartwatch'",
    'story_briefing_completed': "BOOLEAN DEFAULT 0",
    'theory_notes': "TEXT DEFAULT ''",
    'timeline_discoveries': "TEXT DEFAULT ''",
    'authorized_round': "INTEGER DEFAULT 1",
    'round_completed': "BOOLEAN DEFAULT 0",
}

ROUND_CONFIG_MIGRATIONS = {
    'status': "TEXT DEFAULT 'LOCKED'",
    'started_at': "DATETIME",
    'duration_minutes': "INTEGER DEFAULT 30",
}


def migrate_database(database_path):
    """Apply additive SQLite migrations without replacing existing data."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        # Migrate team table
        existing_team_columns = {
            row[1] for row in connection.execute('PRAGMA table_info(team)')
        }
        added_columns = []
        if existing_team_columns:
            for column_name, definition in TEAM_MIGRATIONS.items():
                if column_name not in existing_team_columns:
                    connection.execute(
                        f'ALTER TABLE team ADD COLUMN {column_name} {definition}'
                    )
                    added_columns.append(f'team.{column_name}')

        # Migrate round_config table
        existing_rc_columns = {
            row[1] for row in connection.execute('PRAGMA table_info(round_config)')
        }
        if existing_rc_columns:
            for column_name, definition in ROUND_CONFIG_MIGRATIONS.items():
                if column_name not in existing_rc_columns:
                    connection.execute(
                        f'ALTER TABLE round_config ADD COLUMN {column_name} {definition}'
                    )
                    added_columns.append(f'round_config.{column_name}')

        connection.commit()
        return added_columns