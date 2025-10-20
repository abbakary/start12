#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from tracker.models import Order

# Update consultation orders to inquiry
updated_count = Order.objects.filter(type='consultation').update(type='inquiry')
print(f"Updated {updated_count} orders from 'consultation' to 'inquiry'")

# Show current counts
total_orders = Order.objects.count()
inquiry_orders = Order.objects.filter(type='inquiry').count()
service_orders = Order.objects.filter(type='service').count()
sales_orders = Order.objects.filter(type='sales').count()

print(f"Total orders: {total_orders}")
print(f"Inquiry orders: {inquiry_orders}")
print(f"Service orders: {service_orders}")
print(f"Sales orders: {sales_orders}")