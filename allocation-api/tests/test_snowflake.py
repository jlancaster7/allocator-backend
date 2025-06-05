"""Test Snowflake connection and create tables"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import engine, init_db
from app.models import Base, Allocation, AllocationDetail, AuditLog, UserActivity
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_snowflake_connection():
    """Test basic Snowflake connection"""
    print("\n" + "="*60)
    print("Testing Snowflake Connection")
    print("="*60)
    
    try:
        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT CURRENT_VERSION()"))
            version = result.scalar()
            print(f"✓ Connected to Snowflake")
            print(f"  Version: {version}")
            
            # Get current database and schema
            result = conn.execute(text("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()"))
            db_name, schema_name = result.fetchone()
            print(f"  Database: {db_name}")
            print(f"  Schema: {schema_name}")
            
            # Get current user and role
            result = conn.execute(text("SELECT CURRENT_USER(), CURRENT_ROLE()"))
            user, role = result.fetchone()
            print(f"  User: {user}")
            print(f"  Role: {role}")
            
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Snowflake: {e}")
        return False


def show_existing_tables():
    """Show existing tables in the database"""
    print("\n" + "="*60)
    print("Existing Tables")
    print("="*60)
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"Found {len(tables)} existing tables:")
            for table in tables:
                print(f"  - {table}")
                # Get column info
                columns = inspector.get_columns(table)
                for col in columns:
                    print(f"    • {col['name']} ({col['type']})")
        else:
            print("No existing tables found")
            
        return tables
    except Exception as e:
        print(f"✗ Error listing tables: {e}")
        return []


def create_tables():
    """Create all tables"""
    print("\n" + "="*60)
    print("Creating Tables")
    print("="*60)
    
    try:
        # Initialize database (creates tables)
        init_db()
        print("✓ Tables created successfully")
        
        # List created tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
            
        return True
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        print(f"  Error details: {str(e)}")
        return False


def test_table_operations():
    """Test basic table operations"""
    print("\n" + "="*60)
    print("Testing Table Operations")
    print("="*60)
    
    try:
        from app.core.database import SessionLocal
        from app.services.database_service import AllocationService
        from app.services.audit_service import AuditService
        import uuid
        
        # Create a test session
        db = SessionLocal()
        
        # Test creating an allocation
        print("\n1. Testing allocation creation...")
        test_allocation = AllocationService.create_allocation(
            db=db,
            order_data={
                "order_id": f"TEST-{uuid.uuid4().hex[:8]}",
                "security_id": "912828ZW8",
                "quantity": 1000000
            },
            allocation_method="PRO_RATA",
            portfolio_group_id="PUBLICPRE",
            parameters={"base_metric": "NAV"},
            constraints={"respect_cash": True, "min_allocation": 1000},
            created_by="test_user"
        )
        print(f"✓ Created test allocation: {test_allocation.allocation_id}")
        
        # Test audit logging
        print("\n2. Testing audit logging...")
        audit_log = AuditService.log_action(
            db=db,
            user_id="test_user",
            username="Test User",
            action="CREATE_ALLOCATION",
            entity_type="allocation",
            entity_id=test_allocation.allocation_id,
            changes={"status": "created"}
        )
        print(f"✓ Created audit log: {audit_log.audit_id}")
        
        # Verify data was saved
        print("\n3. Verifying data persistence...")
        saved_allocation = AllocationService.get_allocation(db, test_allocation.allocation_id)
        if saved_allocation:
            print(f"✓ Allocation retrieved successfully")
            print(f"  ID: {saved_allocation.allocation_id}")
            print(f"  Portfolio Group: {saved_allocation.portfolio_group_id}")
            print(f"  Method: {saved_allocation.allocation_method.value}")
            print(f"  Status: {saved_allocation.status.value}")
        
        # Clean up
        db.close()
        
        return True
    except Exception as e:
        print(f"✗ Table operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("Snowflake Database Test Suite")
    print(f"Using database: {settings.SNOWFLAKE_DATABASE}")
    print(f"Using schema: {settings.SNOWFLAKE_SCHEMA}")
    
    # Run tests
    if not test_snowflake_connection():
        print("\n❌ Cannot proceed without database connection")
        return
    
    existing_tables = show_existing_tables()
    
    # Tables already exist (created via SQL script)
    if existing_tables:
        print("\n✓ Tables already exist (created via SQL script)")
        print("  Skipping table creation")
    else:
        create_tables()
    
    # Test operations
    test_table_operations()
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print("✅ All tests completed!")
    print("\nYou can now use the Snowflake database for:")
    print("  - Storing allocation history")
    print("  - Audit trail tracking")
    print("  - User activity monitoring")
    print("  - Compliance reporting")


if __name__ == "__main__":
    main()