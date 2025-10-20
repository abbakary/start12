#!/usr/bin/env python
"""
Test script to check notification API functionality.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from tracker.models import Customer, Order, InventoryItem
from tracker.views import api_notifications_summary
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone

def test_notifications_api():
    """Test the notifications API function."""
    print("=== Testing Notifications API ===\n")
    
    # Create a test request
    factory = RequestFactory()
    request = factory.get('/api/notifications/summary/')
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'is_active': True}
    )
    request.user = user
    
    try:
        # Call the API function
        response = api_notifications_summary(request)
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content.decode()}")
        
        # Parse JSON response
        import json
        data = json.loads(response.content.decode())
        
        if data.get('success'):
            counts = data.get('counts', {})
            print(f"\nNotification counts:")
            print(f"  Today's visitors: {counts.get('today_visitors', 0)}")
            print(f"  Low stock items: {counts.get('low_stock', 0)}")
            print(f"  Overdue orders: {counts.get('overdue_orders', 0)}")
            print(f"  Total: {counts.get('total', 0)}")
            
            # Show some sample data
            items = data.get('items', {})
            if items.get('today_visitors'):
                print(f"\nSample visitors:")
                for visitor in items['today_visitors'][:3]:
                    print(f"  - {visitor['name']} ({visitor.get('type', 'unknown')})")
            
            if items.get('low_stock'):
                print(f"\nSample low stock items:")
                for item in items['low_stock'][:3]:
                    print(f"  - {item['name']} (qty: {item['quantity']})")
            
            if items.get('overdue_orders'):
                print(f"\nSample overdue orders:")
                for order in items['overdue_orders'][:3]:
                    print(f"  - {order['order_number']} ({order['customer']})")
        
        else:
            print("API returned success=False")
            
    except Exception as e:
        print(f"Error testing API: {e}")
        import traceback
        traceback.print_exc()

def check_data():
    """Check if there's data to show notifications."""
    print("\n=== Checking Database Data ===\n")
    
    # Check customers
    total_customers = Customer.objects.count()
    today_customers = Customer.objects.filter(registration_date__date=timezone.localdate()).count()
    print(f"Total customers: {total_customers}")
    print(f"Customers registered today: {today_customers}")
    
    # Check orders
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=timezone.localdate()).count()
    overdue_orders = Order.objects.filter(
        status__in=['created', 'in_progress'],
        created_at__lt=timezone.now() - timezone.timedelta(hours=24)
    ).count()
    print(f"Total orders: {total_orders}")
    print(f"Orders created today: {today_orders}")
    print(f"Overdue orders: {overdue_orders}")
    
    # Check inventory
    total_items = InventoryItem.objects.count()
    low_stock_items = InventoryItem.objects.filter(quantity__lte=5).count()
    print(f"Total inventory items: {total_items}")
    print(f"Low stock items (≤5): {low_stock_items}")
    
    if total_customers == 0:
        print("\n⚠️  No customers found! Creating sample data...")
        create_sample_data()

def create_sample_data():
    """Create sample data for testing."""
    print("Creating sample data...")
    
    # Create sample customer
    customer = Customer.objects.create(
        full_name="Test Customer",
        phone="1234567890",
        email="test@example.com",
        customer_type="personal"
    )
    
    # Create sample order
    order = Order.objects.create(
        customer=customer,
        type="service",
        status="in_progress",
        description="Test service order"
    )
    
    # Create sample inventory item
    from tracker.models import Brand
    brand, _ = Brand.objects.get_or_create(name="Test Brand")
    item = InventoryItem.objects.create(
        name="Test Tire",
        brand=brand,
        quantity=2,  # Low stock
        price=100.00
    )
    
    print("✅ Sample data created!")
    return test_notifications_api()

if __name__ == "__main__":
    check_data()
    test_notifications_api()

