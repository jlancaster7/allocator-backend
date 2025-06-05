"""Test script to verify the application setup is working correctly"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all major imports work"""
    print("Testing imports...")
    
    try:
        # Core imports
        from app.core.config import settings
        print("✓ Config module imported successfully")
        
        from app.core.database import get_db
        print("✓ Database module imported successfully")
        
        from app.core.logging import setup_logging, get_logger
        print("✓ Logging module imported successfully")
        
        from app.core.security import create_access_token, verify_password
        print("✓ Security module imported successfully")
        
        from app.core.auth import get_current_user, require_auth
        print("✓ Auth module imported successfully")
        
        # Service imports
        from app.services.aladdin_client import AladdinClient
        print("✓ Aladdin client imported successfully")
        
        from app.services.allocation_engines import (
            ProRataAllocationEngine,
            CustomWeightsAllocationEngine,
            MinimumDispersionAllocationEngine,
            AllocationEngineFactory
        )
        print("✓ All allocation engines imported successfully")
        
        # API imports
        from app.api import auth, portfolios, securities
        print("✓ API modules imported successfully")
        
        # Flask app
        from app.create_app import create_app
        print("✓ Flask app factory imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import settings
        
        print(f"✓ API Version: {settings.API_V1_STR}")
        print(f"✓ Project Name: {settings.PROJECT_NAME}")
        print(f"✓ Debug Mode: {settings.DEBUG}")
        print(f"✓ JWT Algorithm: {settings.JWT_ALGORITHM}")
        print(f"✓ Rate Limit: {settings.ALADDIN_RATE_LIMIT_PER_MINUTE} requests/minute")
        
        # Check for required environment variables
        missing_vars = []
        
        if not settings.ALADDIN_CLIENT_ID:
            missing_vars.append("ALADDIN_CLIENT_ID")
        if not settings.ALADDIN_CLIENT_SECRET:
            missing_vars.append("ALADDIN_CLIENT_SECRET")
        if not settings.SNOWFLAKE_ACCOUNT:
            missing_vars.append("SNOWFLAKE_ACCOUNT")
            
        if missing_vars:
            print(f"\nNote: The following environment variables are not set: {', '.join(missing_vars)}")
            print("This is expected if you haven't configured .env yet")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_logging():
    """Test logging setup"""
    print("\nTesting logging...")
    
    try:
        from app.core.logging import setup_logging, get_logger
        
        setup_logging()
        logger = get_logger("test_setup")
        
        logger.info("Test log message", extra_field="test_value")
        print("✓ Logging setup successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Logging error: {e}")
        return False


def test_security():
    """Test security functions"""
    print("\nTesting security functions...")
    
    try:
        from app.core.security import (
            create_access_token,
            decode_token,
            get_password_hash,
            verify_password
        )
        
        # Test password hashing
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)
        print("✓ Password hashing working correctly")
        
        # Test JWT token creation and decoding
        user_data = {"sub": "test_user", "username": "test"}
        token = create_access_token(user_data)
        decoded = decode_token(token)
        assert decoded["sub"] == "test_user"
        assert decoded["username"] == "test"
        print("✓ JWT token creation and validation working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Security error: {e}")
        return False


def test_allocation_engines():
    """Test allocation engine instantiation"""
    print("\nTesting allocation engines...")
    
    try:
        from app.services.allocation_engines import (
            AllocationEngineFactory,
            AllocationMethod
        )
        
        # Test factory
        methods = AllocationEngineFactory.get_available_methods()
        print(f"✓ Available allocation methods: {', '.join(methods)}")
        
        # Test each engine creation
        for method_str in methods:
            engine = AllocationEngineFactory.create_from_string(method_str)
            print(f"✓ Created {method_str} engine successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Allocation engine error: {e}")
        return False


def test_flask_app():
    """Test Flask app creation"""
    print("\nTesting Flask app creation...")
    
    try:
        from app.create_app import create_app
        
        app = create_app()
        
        # Check that app was created
        assert app is not None
        print("✓ Flask app created successfully")
        
        # Check routes are registered
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        
        # Check for some expected routes
        expected_routes = [
            "/api/v1/auth/login",
            "/api/v1/portfolio-groups",
            "/api/v1/securities/search"
        ]
        
        for route in expected_routes:
            if any(route in rule for rule in rules):
                print(f"✓ Route registered: {route}")
            else:
                print(f"✗ Route missing: {route}")
        
        return True
        
    except Exception as e:
        print(f"✗ Flask app error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Order Allocation System - Setup Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_configuration,
        test_logging,
        test_security,
        test_allocation_engines,
        test_flask_app
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\nUnexpected error in {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! The setup is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)