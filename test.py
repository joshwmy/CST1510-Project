# test.py 
from app.data.schema import init_schema
from app.data.csv_loader import load_all_csv_data, verify_data_loading

print("Starting database setup...")
init_schema()
print("Schema created!")
load_all_csv_data()
print("Data loaded!")
verify_data_loading()
print("All done! ")


import os
from app.data.schema import init_schema
from app.data.csv_loader import load_all_csv_data, verify_data_loading
from app.services.user_service import migrate_users_from_file
from app.data.db import connect_database

def main():
    print(" Initializing database schema...")
    
    db_path = "DATA/intelligence_platform.db"
    if os.path.exists(db_path):
        print("📁 Removing existing database...")
        os.remove(db_path)
    
    # Initialize schema
    print(" Creating tables...")
    init_schema()
    
    # Load sample data
    print("Loading CSV data...")
    results = load_all_csv_data()
    
    # Migrate users from users.txt
    print("👥 Migrating users from users.txt...")
    conn = connect_database()
    migrate_users_from_file(conn)
    conn.close()
    
    # Verify loading
    print("Verifying data...")
    verify_data_loading()
    
    print("Database setup complete!")
    print(f"Results: {results}")

if __name__ == "__main__":
    main()