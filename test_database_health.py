# test_database_health.py
import os
import django
from django.db import connection, models
from django.apps import apps
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

def test_database_health():
    print("=" * 60)
    print("DATABASE HEALTH CHECK")
    print("=" * 60)
    
    # Test 1: Basic Connection
    print("\n1. 🔌 Testing Database Connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # Test 2: Database Information
    print("\n2. 📊 Database Information...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATABASE(),
                    @@version,
                    @@character_set_database,
                    @@collation_database,
                    @@time_zone,
                    @@sql_mode
            """)
            db_name, version, charset, collation, tz, sql_mode = cursor.fetchone()
            print(f"✅ Database: {db_name}")
            print(f"✅ MySQL Version: {version}")
            print(f"✅ Character Set: {charset}")
            print(f"✅ Collation: {collation}")
            print(f"✅ Time Zone: {tz}")
            print(f"✅ SQL Mode: {sql_mode}")
    except Exception as e:
        print(f"❌ Database info failed: {e}")

    # Test 3: List All Tables
    print("\n3. 📋 Checking Database Tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            print(f"✅ Tables found: {len(tables)}")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count} records")
    except Exception as e:
        print(f"❌ Table check failed: {e}")

    # Test 4: Django Model Integration
    print("\n4. 🔄 Testing Django Models...")
    try:
        for model in apps.get_models():
            try:
                count = model.objects.count()
                print(f"✅ {model._meta.label}: {count} records")
            except Exception as e:
                print(f"⚠️  {model._meta.label}: Error - {e}")
    except Exception as e:
        print(f"❌ Model test failed: {e}")

    # Test 5: Timezone Compatibility
    print("\n5. ⏰ Testing Timezone Settings...")
    try:
        from django.utils import timezone
        current_time = timezone.now()
        print(f"✅ Django timezone: {current_time}")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT NOW(), UTC_TIMESTAMP()")
            mysql_now, mysql_utc = cursor.fetchone()
            print(f"✅ MySQL server time: {mysql_now}")
            print(f"✅ MySQL UTC time: {mysql_utc}")
    except Exception as e:
        print(f"❌ Timezone test failed: {e}")

    # Test 6: Transaction Support
    print("\n6. 💾 Testing Transactions...")
    try:
        from django.db import transaction
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT @@autocommit, @@transaction_isolation")
                autocommit, isolation = cursor.fetchone()
                print(f"✅ Autocommit: {autocommit}")
                print(f"✅ Isolation Level: {isolation}")
    except Exception as e:
        print(f"❌ Transaction test failed: {e}")

    print("\n" + "=" * 60)
    print("HEALTH CHECK COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_database_health()