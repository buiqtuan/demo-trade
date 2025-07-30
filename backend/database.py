from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://username:password@localhost:5432/trading_simulator"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    """
    Dependency function to get database session.
    Ensures session is properly closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database utility functions
def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    Base.metadata.create_all(bind=engine)

def drop_db():
    """
    Drop all database tables.
    Use with caution - this will delete all data!
    """
    Base.metadata.drop_all(bind=engine)

# Test database connection
def test_connection():
    """
    Test database connection.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            return result.fetchone()[0] == 1
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False 