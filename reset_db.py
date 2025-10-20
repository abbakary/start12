import os
import shutil

def reset_database():
    # Remove the database file if it exists
    db_file = 'db.sqlite3'
    if os.path.exists(db_file):
        os.remove(db_file)
    
    # Remove all migration files except __init__.py
    migrations_dir = 'tracker/migrations'
    for filename in os.listdir(migrations_dir):
        if filename != '__init__.py' and filename.endswith('.py'):
            os.remove(os.path.join(migrations_dir, filename))
    
    print("Database and migrations have been reset. Please run the following commands:")
    print("1. python manage.py makemigrations")
    print("2. python manage.py migrate")
    print("3. python manage.py createsuperuser")
    print("4. python manage.py runserver")

if __name__ == "__main__":
    reset_database()
