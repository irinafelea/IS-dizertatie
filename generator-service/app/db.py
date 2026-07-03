from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = ""

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Yields a database session

    Args:
        None

    Returns:
        Database session generator
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
