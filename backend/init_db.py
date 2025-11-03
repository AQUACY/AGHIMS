"""
Database initialization script
Creates tables and default admin user
"""
from app.core.database import Base, engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

# Import all models to ensure they're registered with Base
import app.models  # This imports all models from __init__.py

def init_db():
    """Initialize database with tables"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    # Create default admin user
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@hms.local",
                hashed_password=get_password_hash("admin123"),
                full_name="System Administrator",
                role="Admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("✓ Default admin user created (username: admin, password: admin123)")
        else:
            print("✓ Admin user already exists")
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete!")

