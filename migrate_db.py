import sqlite3

DATABASE_FILE = 'database.db'

def migrate_sessions():
    print("--- Starting Sessions Table Migration ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Get the list of columns currently in the 'sessions' table
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns in 'sessions': {columns}")

        # List of columns to check for and add
        columns_to_add = {
            'video1_url': 'TEXT',
            'video2_url': 'TEXT',
            'video3_url': 'TEXT',
            'video4_url': 'TEXT',
            'duration_weeks': 'INTEGER DEFAULT 0',
            'student_count': 'INTEGER DEFAULT 0'
        }

        for col_name, col_type in columns_to_add.items():
            if col_name not in columns:
                print(f"Adding '{col_name}' column to sessions table...")
                cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}")
                print(f"'{col_name}' column added successfully.")
            else:
                print(f"'{col_name}' column already exists.")
        
        conn.commit()
        print("\nMigration for sessions table complete. Your database is now up to date.")

    except sqlite3.Error as e:
        print(f"DATABASE ERROR: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_sessions()
