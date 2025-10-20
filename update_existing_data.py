#!/usr/bin/env python3
"""
Update Existing Data Script
===========================
This script updates existing database records to remove bodaboda customer types
and standardize tire types to only "New"
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from tracker.models import Customer, Order

def update_customer_types():
    """Update bodaboda customers to personal type"""
    print("Updating customer types...")
    
    # Update bodaboda customers to personal
    bodaboda_customers = Customer.objects.filter(customer_type='bodaboda')
    count = bodaboda_customers.count()
    
    if count > 0:
        bodaboda_customers.update(customer_type='personal')
        print(f"Updated {count} bodaboda customers to personal type")
    else:
        print("No bodaboda customers found")

def update_tire_types():
    """Update tire types to only New"""
    print("Updating tire types...")
    
    # Update used and refurbished to new
    used_orders = Order.objects.filter(tire_type__in=['Used', 'Refurbished', 'used', 'refurbished'])
    count = used_orders.count()
    
    if count > 0:
        used_orders.update(tire_type='New')
        print(f"Updated {count} orders with used/refurbished tires to new")
    else:
        print("No used/refurbished tire orders found")

def main():
    """Main function"""
    print("Updating existing data...")
    print("=" * 40)
    
    try:
        update_customer_types()
        update_tire_types()
        
        print("=" * 40)
        print("Data update completed successfully!")
        
    except Exception as e:
        print(f"Error updating data: {e}")

if __name__ == '__main__':
    main()