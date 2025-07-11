from app import app, db, User # Import your app, db instance, and User model
from werkzeug.security import generate_password_hash

# --- CONFIGURATION ---
ADMIN_EMAIL = 'admin@example.com'
NEW_PASSWORD = 'admin'
# ---------------------

print("--- Admin Password Reset Script (SQLAlchemy Version) ---")

# The 'with app.app_context()' is crucial. It makes the script aware of your Flask app's
# configuration, including how to connect to the database.
with app.app_context():
    try:
        print(f"Attempting to find user: {ADMIN_EMAIL}...")
        # Use the User model to query the database
        user = User.query.filter_by(email=ADMIN_EMAIL).first()

        if user:
            print("User found. Generating new password hash...")
            # Update the user object's password attribute
            user.password = generate_password_hash(NEW_PASSWORD)
            
            # Commit the change to the database
            db.session.commit()
            print(f"SUCCESS: Password for {ADMIN_EMAIL} has been updated.")
        else:
            print(f"ERROR: Could not find user with email {ADMIN_EMAIL}.")
            print("Please create the admin user first by running 'flask init-db' in your terminal.")

    except Exception as e:
        print(f"An error occurred: {e}")

print("--- Script finished ---")
