import logging
import subprocess
from urllib.parse import urlparse
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from .base import CA_Base
from app.constants import DATABASE_URL
# Load environment variables from the .env file


# Create the engine for connecting to the database
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# Create SessionLocal for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Import models
from app.model.user import User
from app.model.сlothing_item import ClothingItem
# Base class for creating tables
from app.model import *

# Inspect existing tables in the database
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

# Display existing tables before creating new ones
print("🚀Existing tables in the database:")
for table in existing_tables:
    print(f"- {table}")
print("✅ Registered tables:", CA_Base.metadata.tables.keys())

# Create tables if they do not already exist
CA_Base.metadata.create_all(bind=engine)

# Check for new tables created by create_all
new_tables = set(CA_Base.metadata.tables.keys()) - set(existing_tables)
try:

    parsed_url = urlparse(DATABASE_URL)

    username = parsed_url.username       
    password = parsed_url.password       
    database_name = parsed_url.path.lstrip('/')  

    cmd = [
        'mysql',
        '-u', username,
        f'-p{password}', 
        database_name
    ]

    with open('app/database/init_function.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(input=sql_script)
    if process.returncode == 0:
        logging.info("SQL script executed successfully.")
        if stdout.strip():
            logging.info("Output:\n%s", stdout)
except Exception as e:
    logging.error("An error occurred while executing the SQL script: %s", e)
    stdout, stderr = "", str(e)

else:
    logging.error("Failed to execute SQL script.")
    logging.error("Return code: %d", process.returncode)
    logging.error("Error output:\n%s", stderr)
# Display newly created tables
if new_tables:
    print(f"🛠️New tables created: {', '.join(new_tables)}")
else:
    print("Tables already exist or no new tables were created.")

# Dependency for getting the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
