from pathlib import Path

from app.database import migrate_database


if __name__ == '__main__':
    database_path = Path(__file__).resolve().parent / 'instance' / 'murder_case.db'
    added_columns = migrate_database(database_path)
    if added_columns:
        print(f"Added columns: {', '.join(added_columns)}")
    else:
        print('Database schema is already up to date.')