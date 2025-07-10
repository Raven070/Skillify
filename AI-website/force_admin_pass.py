import sqlite3
from werkzeug.security import generate_password_hash

# --- CONFIGURATION ---
DATABASE_FILE = 'database.db'
ADMIN_EMAIL = 'admin@example.com'
NEW_PASSWORD = 'admin'
# ---------------------

print("--- Admin Password Reset Script ---")

try:
    # Connect to the database
    print(f"Connecting to database file: {DATABASE_FILE}...")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    print("Connection successful.")

    # Generate a new secure hash for the password 'admin'
    print(f"Generating new password hash for password: '{NEW_PASSWORD}'...")
    new_hash = generate_password_hash(NEW_PASSWORD)
    print("New hash generated.")

    # Update the user's password in the database
    print(f"Attempting to update password for user: {ADMIN_EMAIL}...")
    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (new_hash, ADMIN_EMAIL))
    
    # Check if the update was successful
    if cursor.rowcount > 0:
        conn.commit()
        print(f"SUCCESS: Password for {ADMIN_EMAIL} has been updated.")
    else:
        print(f"ERROR: Could not find user with email {ADMIN_EMAIL}. Please register the admin user first by running 'flask --app app init-db'.")

except sqlite3.Error as e:
    print(f"DATABASE ERROR: {e}")
finally:
    if conn:
        conn.close()
        print("Database connection closed.")

print("--- Script finished ---")