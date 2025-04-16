from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Get DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine for connecting to the database
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# Create SessionLocal for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for creating tables
Base = declarative_base()

# Import models
from app.model.user import User
from app.model.clothing_combination import ClothingCombination
from app.model.сlothing_item import ClothingItem

# Inspect existing tables in the database
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

# Display existing tables before creating new ones
print("🚀Existing tables in the database:")
for table in existing_tables:
    print(f"- {table}")

# Create tables if they do not already exist
Base.metadata.create_all(bind=engine)

# Check for new tables created by create_all
new_tables = set(Base.metadata.tables.keys()) - set(existing_tables)

# Display newly created tables
if new_tables:
    print(f"🛠️New tables created: {', '.join(new_tables)}")
else:
    print("Tables already exist or no new tables were created.")

# Display all tables registered in Base
print("🚀Tables registered in Base:")
for table in Base.metadata.tables:
    print(f"- {table}")

# Dependency for getting the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
