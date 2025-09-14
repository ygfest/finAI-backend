"""
Database Connection Testing Utility

This module provides utilities to test your database connection, especially
useful when setting up Neon PostgreSQL for the first time.

Key Features:
- Test basic connectivity
- Validate SSL configuration
- Check database permissions
- Measure connection performance
- Provide detailed error diagnostics

Usage:
    python -m app.database.test_connection
"""

import asyncio
import sys
import time
from typing import Dict, Any, Optional

from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.engine import Engine

from .core import (
    get_database_url,
    get_database_config,
    get_db_context,
    check_database_connection,
    get_database_info,
    is_postgresql,
    is_sqlite,
)


def test_basic_connection() -> Dict[str, Any]:
    """
    Test basic database connectivity.
    
    Returns:
        Dict containing test results and diagnostics
    """
    print("🔍 Testing basic database connection...")
    
    result = {
        "test": "basic_connection",
        "success": False,
        "error": None,
        "duration_ms": 0,
        "details": {}
    }
    
    start_time = time.time()
    
    try:
        success = check_database_connection()
        result["success"] = success
        result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if success:
            print("✅ Basic connection test PASSED")
            result["details"]["message"] = "Database connection successful"
        else:
            print("❌ Basic connection test FAILED")
            result["details"]["message"] = "Database connection failed"
            
    except Exception as e:
        result["error"] = str(e)
        result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        print(f"❌ Basic connection test ERROR: {e}")
    
    return result


def test_database_info() -> Dict[str, Any]:
    """
    Test database information retrieval.
    
    Returns:
        Dict containing database configuration info
    """
    print("📊 Testing database information retrieval...")
    
    result = {
        "test": "database_info",
        "success": False,
        "error": None,
        "info": {}
    }
    
    try:
        db_info = get_database_info()
        result["success"] = True
        result["info"] = db_info
        
        print("✅ Database info test PASSED")
        print(f"   Database Type: {db_info.get('database_type')}")
        print(f"   Database URL: {db_info.get('database_url')}")
        
        if is_postgresql:
            print(f"   Pool Size: {db_info.get('pool_size')}")
            print(f"   Max Overflow: {db_info.get('max_overflow')}")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Database info test ERROR: {e}")
    
    return result


def test_sql_queries() -> Dict[str, Any]:
    """
    Test basic SQL query execution.
    
    Returns:
        Dict containing query test results
    """
    print("🔍 Testing SQL query execution...")
    
    result = {
        "test": "sql_queries",
        "success": False,
        "error": None,
        "queries": []
    }
    
    # Test queries based on database type
    if is_postgresql:
        test_queries = [
            ("SELECT 1 as test", "Basic SELECT"),
            ("SELECT version()", "PostgreSQL version"),
            ("SELECT current_database()", "Current database"),
            ("SELECT current_user", "Current user"),
            ("SELECT now()", "Current timestamp"),
        ]
    else:
        test_queries = [
            ("SELECT 1 as test", "Basic SELECT"),
            ("SELECT sqlite_version()", "SQLite version"),
        ]
    
    try:
        with get_db_context() as db:
            for query, description in test_queries:
                query_result = {
                    "query": query,
                    "description": description,
                    "success": False,
                    "result": None,
                    "error": None
                }
                
                try:
                    start_time = time.time()
                    db_result = db.execute(text(query))
                    row = db_result.fetchone()
                    duration = round((time.time() - start_time) * 1000, 2)
                    
                    query_result["success"] = True
                    query_result["result"] = str(row[0]) if row else None
                    query_result["duration_ms"] = duration
                    
                    print(f"   ✅ {description}: {query_result['result']} ({duration}ms)")
                    
                except Exception as e:
                    query_result["error"] = str(e)
                    print(f"   ❌ {description}: {e}")
                
                result["queries"].append(query_result)
        
        # Check if all queries succeeded
        result["success"] = all(q["success"] for q in result["queries"])
        
        if result["success"]:
            print("✅ SQL queries test PASSED")
        else:
            print("❌ Some SQL queries FAILED")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ SQL queries test ERROR: {e}")
    
    return result


def test_connection_pooling() -> Dict[str, Any]:
    """
    Test connection pooling (PostgreSQL only).
    
    Returns:
        Dict containing pooling test results
    """
    print("🏊 Testing connection pooling...")
    
    result = {
        "test": "connection_pooling",
        "success": False,
        "error": None,
        "details": {}
    }
    
    if not is_postgresql:
        result["success"] = True
        result["details"]["message"] = "Skipped - SQLite doesn't use connection pooling"
        print("⏭️  Connection pooling test SKIPPED (SQLite)")
        return result
    
    try:
        # Create multiple connections to test pooling
        database_url = get_database_url()
        db_config = get_database_config()
        
        # Create engine with small pool for testing
        test_engine = create_engine(
            database_url,
            pool_size=2,
            max_overflow=1,
            pool_timeout=5,
            pool_pre_ping=True,
            connect_args={"sslmode": "require"}
        )
        
        connections = []
        start_time = time.time()
        
        # Test creating multiple connections
        for i in range(3):  # This should use pool + overflow
            conn = test_engine.connect()
            connections.append(conn)
            
            # Execute a simple query
            result_proxy = conn.execute(text("SELECT 1"))
            result_proxy.fetchone()
            
            print(f"   ✅ Connection {i+1} established")
        
        duration = round((time.time() - start_time) * 1000, 2)
        
        # Clean up connections
        for conn in connections:
            conn.close()
        
        test_engine.dispose()
        
        result["success"] = True
        result["details"]["connections_tested"] = len(connections)
        result["details"]["duration_ms"] = duration
        result["details"]["pool_size"] = db_config["pool_size"]
        result["details"]["max_overflow"] = db_config["max_overflow"]
        
        print(f"✅ Connection pooling test PASSED ({duration}ms)")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Connection pooling test ERROR: {e}")
        
        # Clean up on error
        try:
            for conn in connections:
                conn.close()
            if 'test_engine' in locals():
                test_engine.dispose()
        except:
            pass
    
    return result


def test_ssl_connection() -> Dict[str, Any]:
    """
    Test SSL connection (PostgreSQL only).
    
    Returns:
        Dict containing SSL test results
    """
    print("🔒 Testing SSL connection...")
    
    result = {
        "test": "ssl_connection",
        "success": False,
        "error": None,
        "details": {}
    }
    
    if not is_postgresql:
        result["success"] = True
        result["details"]["message"] = "Skipped - SQLite doesn't use SSL"
        print("⏭️  SSL connection test SKIPPED (SQLite)")
        return result
    
    try:
        with get_db_context() as db:
            # Query SSL status
            ssl_query = text("SELECT ssl_is_used() as ssl_enabled")
            ssl_result = db.execute(ssl_query)
            ssl_row = ssl_result.fetchone()
            
            if ssl_row and ssl_row[0]:
                result["success"] = True
                result["details"]["ssl_enabled"] = True
                result["details"]["message"] = "SSL connection is active"
                print("✅ SSL connection test PASSED - SSL is enabled")
            else:
                result["success"] = False
                result["details"]["ssl_enabled"] = False
                result["details"]["message"] = "SSL connection is not active"
                print("⚠️  SSL connection test WARNING - SSL is not enabled")
                
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ SSL connection test ERROR: {e}")
    
    return result


def test_performance() -> Dict[str, Any]:
    """
    Test basic database performance.
    
    Returns:
        Dict containing performance test results
    """
    print("⚡ Testing database performance...")
    
    result = {
        "test": "performance",
        "success": False,
        "error": None,
        "metrics": {}
    }
    
    try:
        # Test multiple connection attempts
        connection_times = []
        query_times = []
        
        for i in range(5):
            # Test connection time
            start_time = time.time()
            with get_db_context() as db:
                connection_time = (time.time() - start_time) * 1000
                connection_times.append(connection_time)
                
                # Test query time
                query_start = time.time()
                db.execute(text("SELECT 1"))
                query_time = (time.time() - query_start) * 1000
                query_times.append(query_time)
        
        # Calculate metrics
        avg_connection_time = sum(connection_times) / len(connection_times)
        avg_query_time = sum(query_times) / len(query_times)
        max_connection_time = max(connection_times)
        max_query_time = max(query_times)
        
        result["success"] = True
        result["metrics"] = {
            "avg_connection_time_ms": round(avg_connection_time, 2),
            "avg_query_time_ms": round(avg_query_time, 2),
            "max_connection_time_ms": round(max_connection_time, 2),
            "max_query_time_ms": round(max_query_time, 2),
            "samples": len(connection_times)
        }
        
        print(f"✅ Performance test PASSED")
        print(f"   Avg Connection Time: {avg_connection_time:.2f}ms")
        print(f"   Avg Query Time: {avg_query_time:.2f}ms")
        print(f"   Max Connection Time: {max_connection_time:.2f}ms")
        print(f"   Max Query Time: {max_query_time:.2f}ms")
        
        # Warn about slow connections (typical for Neon cold starts)
        if avg_connection_time > 1000:
            print("   ⚠️  Connection time is high - this is normal for Neon cold starts")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Performance test ERROR: {e}")
    
    return result


def run_all_tests() -> Dict[str, Any]:
    """
    Run all database tests.
    
    Returns:
        Dict containing all test results
    """
    print("🧪 Running comprehensive database tests...\n")
    
    # Get database configuration
    database_url = get_database_url()
    print(f"Database URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    print(f"Database Type: {'PostgreSQL (Neon)' if is_postgresql else 'SQLite'}")
    print("-" * 60)
    
    # Run all tests
    tests = [
        test_basic_connection,
        test_database_info,
        test_sql_queries,
        test_connection_pooling,
        test_ssl_connection,
        test_performance,
    ]
    
    results = {
        "database_type": "PostgreSQL" if is_postgresql else "SQLite",
        "database_url": database_url.split("@")[-1] if "@" in database_url else database_url,
        "timestamp": time.time(),
        "tests": []
    }
    
    for test_func in tests:
        print()  # Add spacing between tests
        test_result = test_func()
        results["tests"].append(test_result)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for test in results["tests"] if test["success"])
    total = len(results["tests"])
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests PASSED! Your database is ready to use.")
    else:
        print("⚠️  Some tests FAILED. Check the errors above.")
        
        # Show failed tests
        failed_tests = [test for test in results["tests"] if not test["success"]]
        for test in failed_tests:
            print(f"   ❌ {test['test']}: {test.get('error', 'Unknown error')}")
    
    return results


def main():
    """
    Main function for running database connection tests.
    """
    print("🏦 Finance App Database Connection Tester")
    print("=" * 60)
    
    try:
        results = run_all_tests()
        
        # Exit with error code if tests failed
        passed = sum(1 for test in results["tests"] if test["success"])
        total = len(results["tests"])
        
        if passed < total:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
🚀 How to use this testing utility:

1. Set up your environment variables:
   ```bash
   # Copy env.example to .env and configure your Neon connection
   cp env.example .env
   ```

2. Run the tests:
   ```bash
   # From the backend directory
   python -m app.database.test_connection
   ```

3. Interpret the results:
   - ✅ Green checkmarks = Tests passed
   - ❌ Red X marks = Tests failed
   - ⚠️  Yellow warnings = Tests passed with warnings
   - ⏭️  Blue arrows = Tests skipped (not applicable)

4. Common issues and solutions:

   Connection Timeout:
   - Check your DATABASE_URL is correct
   - Verify your Neon project is not paused
   - Check your internet connection

   SSL Errors:
   - Ensure your connection string includes ?sslmode=require
   - Verify you're using the correct Neon endpoint

   Permission Errors:
   - Check your database user has the correct permissions
   - Verify you're connecting to the correct database

   High Latency:
   - This is normal for Neon cold starts
   - Performance improves after the first few connections

📚 Learn More:
- Neon Documentation: https://neon.tech/docs/
- SQLAlchemy Connection Guide: https://docs.sqlalchemy.org/en/20/core/connections.html
- PostgreSQL SSL Documentation: https://www.postgresql.org/docs/current/ssl-tcp.html
"""




