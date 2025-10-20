#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
import random

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from tracker.models import Customer, Vehicle, Order, Brand, InventoryItem
from django.utils import timezone

def create_sample_data():
    print("Creating sample data...")
    
    # Create Brands
    brands_data = [
        {'name': 'Michelin', 'description': 'Premium tire manufacturer'},
        {'name': 'Bridgestone', 'description': 'Leading tire technology'},
        {'name': 'Goodyear', 'description': 'Trusted tire brand'},
        {'name': 'Continental', 'description': 'German engineering'},
        {'name': 'Pirelli', 'description': 'Performance tires'},
        {'name': 'Dunlop', 'description': 'Racing heritage'},
    ]
    
    brands = []
    for brand_data in brands_data:
        brand, created = Brand.objects.get_or_create(
            name=brand_data['name'],
            defaults={'description': brand_data['description']}
        )
        brands.append(brand)
        if created:
            print(f"Created brand: {brand.name}")
    
    # Create Inventory Items
    tire_types = ['All Season', 'Summer', 'Winter', 'Performance', 'Off-Road']
    sizes = ['195/65R15', '205/55R16', '225/45R17', '235/40R18', '245/35R19']
    
    inventory_items = []
    for brand in brands:
        for i in range(3):  # 3 items per brand
            tire_type = random.choice(tire_types)
            size = random.choice(sizes)
            item_name = f"{tire_type} {size}"
            
            item, created = InventoryItem.objects.get_or_create(
                name=item_name,
                brand=brand,
                defaults={
                    'quantity': random.randint(10, 100),
                    'price': random.randint(80, 300),
                    'cost_price': random.randint(50, 200),
                    'reorder_level': random.randint(5, 15),
                    'location': f"Rack {random.randint(1, 10)}"
                }
            )
            inventory_items.append(item)
            if created:
                print(f"Created inventory item: {brand.name} - {item_name}")
    
    # Sample customer data
    customers_data = [
        {'name': 'John Smith', 'phone': '+256701234567', 'email': 'john.smith@email.com', 'type': 'personal', 'subtype': 'owner'},
        {'name': 'Sarah Johnson', 'phone': '+256701234568', 'email': 'sarah.j@email.com', 'type': 'personal', 'subtype': 'driver'},
        {'name': 'Michael Brown', 'phone': '+256701234569', 'email': 'mike.brown@email.com', 'type': 'personal', 'subtype': 'owner'},
        {'name': 'Uganda Revenue Authority', 'phone': '+256701234570', 'email': 'fleet@ura.go.ug', 'type': 'government', 'org': 'Uganda Revenue Authority'},
        {'name': 'Red Cross Uganda', 'phone': '+256701234571', 'email': 'logistics@redcross.ug', 'type': 'ngo', 'org': 'Red Cross Uganda'},
        {'name': 'MTN Uganda Ltd', 'phone': '+256701234572', 'email': 'fleet@mtn.co.ug', 'type': 'company', 'org': 'MTN Uganda Limited'},
        {'name': 'David Wilson', 'phone': '+256701234573', 'email': 'david.w@email.com', 'type': 'personal', 'subtype': 'owner'},
        {'name': 'Ministry of Health', 'phone': '+256701234574', 'email': 'transport@health.go.ug', 'type': 'government', 'org': 'Ministry of Health'},
        {'name': 'UNICEF Uganda', 'phone': '+256701234575', 'email': 'ops@unicef.org', 'type': 'ngo', 'org': 'UNICEF Uganda'},
        {'name': 'Stanbic Bank Uganda', 'phone': '+256701234576', 'email': 'fleet@stanbic.co.ug', 'type': 'company', 'org': 'Stanbic Bank Uganda Limited'},
        {'name': 'Grace Nakato', 'phone': '+256701234577', 'email': 'grace.n@email.com', 'type': 'personal', 'subtype': 'driver'},
        {'name': 'Robert Okello', 'phone': '+256701234578', 'email': 'robert.o@email.com', 'type': 'personal', 'subtype': 'owner'},
        {'name': 'World Vision Uganda', 'phone': '+256701234579', 'email': 'logistics@wvi.org', 'type': 'ngo', 'org': 'World Vision Uganda'},
        {'name': 'Airtel Uganda Ltd', 'phone': '+256701234580', 'email': 'fleet@airtel.co.ug', 'type': 'company', 'org': 'Airtel Uganda Limited'},
        {'name': 'Uganda Police Force', 'phone': '+256701234581', 'email': 'transport@police.go.ug', 'type': 'government', 'org': 'Uganda Police Force'},
    ]
    
    customers = []
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=customer_data['phone'],
            defaults={
                'full_name': customer_data['name'],
                'email': customer_data['email'],
                'customer_type': customer_data['type'],
                'personal_subtype': customer_data.get('subtype'),
                'organization_name': customer_data.get('org'),
                'registration_date': timezone.now() - timedelta(days=random.randint(30, 365)),
                'address': f"Plot {random.randint(1, 999)}, {random.choice(['Kampala', 'Entebbe', 'Jinja', 'Mbarara', 'Gulu'])} Road"
            }
        )
        customers.append(customer)
        if created:
            print(f"Created customer: {customer.full_name}")
    
    # Create vehicles for customers
    vehicle_makes = ['Toyota', 'Honda', 'Nissan', 'Mitsubishi', 'Isuzu', 'Mercedes', 'Volvo', 'Scania']
    vehicle_models = ['Camry', 'Corolla', 'Hilux', 'Prado', 'Civic', 'CRV', 'X-Trail', 'Pajero', 'Canter', 'Actros']
    vehicle_types = ['sedan', 'suv', 'truck', 'van', 'bus']
    
    vehicles = []
    for customer in customers:
        # Each customer gets 1-3 vehicles
        num_vehicles = random.randint(1, 3)
        for i in range(num_vehicles):
            plate_number = f"U{random.choice(['A', 'B', 'C'])}{random.randint(100, 999)}{random.choice(['A', 'B', 'C', 'D', 'E'])}"
            
            vehicle, created = Vehicle.objects.get_or_create(
                plate_number=plate_number,
                defaults={
                    'customer': customer,
                    'make': random.choice(vehicle_makes),
                    'model': random.choice(vehicle_models),
                    'vehicle_type': random.choice(vehicle_types)
                }
            )
            vehicles.append(vehicle)
            if created:
                print(f"Created vehicle: {vehicle.plate_number} for {customer.full_name}")
    
    # Create orders with different statuses and types across different time periods
    order_types = ['service', 'sales', 'inquiry']
    statuses = ['created', 'in_progress', 'completed', 'cancelled', 'overdue']
    priorities = ['low', 'medium', 'high', 'urgent']
    inquiry_types = ['Pricing', 'Services', 'Appointment Booking', 'General']
    contact_preferences = ['phone', 'email', 'whatsapp']
    
    service_types = [
        'Oil Change', 'Brake Service', 'Tire Rotation', 'Engine Tune-up', 
        'Transmission Service', 'Battery Replacement', 'Air Filter Change',
        'Wheel Alignment', 'Suspension Repair', 'Exhaust System Repair'
    ]
    
    orders_created = 0
    
    # Create orders for the last 6 months
    for customer in customers:
        customer_vehicles = list(customer.vehicles.all())
        if not customer_vehicles:
            continue
            
        # Each customer gets 2-8 orders
        num_orders = random.randint(2, 8)
        
        for i in range(num_orders):
            # Random date in the last 6 months
            days_ago = random.randint(1, 180)
            order_date = timezone.now() - timedelta(days=days_ago)
            
            order_type = random.choice(order_types)
            status = random.choice(statuses)
            priority = random.choice(priorities)
            vehicle = random.choice(customer_vehicles) if customer_vehicles else None
            
            order_data = {
                'customer': customer,
                'vehicle': vehicle,
                'type': order_type,
                'status': status,
                'priority': priority,
                'created_at': order_date,
            }
            
            # Set status-specific timestamps
            if status in ['in_progress', 'completed', 'cancelled']:
                order_data['started_at'] = order_date + timedelta(minutes=random.randint(10, 120))
            
            if status == 'completed':
                order_data['completed_at'] = order_data['started_at'] + timedelta(hours=random.randint(1, 8))
            elif status == 'cancelled':
                order_data['cancelled_at'] = order_data['started_at'] + timedelta(minutes=random.randint(30, 240))
                order_data['cancellation_reason'] = random.choice([
                    'Customer cancelled', 'Parts not available', 'Customer no-show', 'Technical issues'
                ])
            
            # Type-specific fields
            if order_type == 'service':
                order_data.update({
                    'description': f"{random.choice(service_types)} for {vehicle.make if vehicle else 'vehicle'}",
                    'estimated_duration': random.randint(60, 480),  # 1-8 hours in minutes
                })
                if status == 'completed':
                    order_data['actual_duration'] = random.randint(
                        int(order_data['estimated_duration'] * 0.8),
                        int(order_data['estimated_duration'] * 1.2)
                    )
            
            elif order_type == 'sales':
                item = random.choice(inventory_items)
                order_data.update({
                    'item_name': item.name,
                    'brand': item.brand.name,
                    'quantity': random.randint(1, 4),
                    'tire_type': random.choice(tire_types),
                    'description': f"Sale of {item.brand.name} {item.name}"
                })
            
            elif order_type == 'inquiry':
                order_data.update({
                    'inquiry_type': random.choice(inquiry_types),
                    'contact_preference': random.choice(contact_preferences),
                    'questions': random.choice([
                        'What are your tire prices for SUVs?',
                        'Do you offer wheel alignment services?',
                        'Can I book an appointment for next week?',
                        'What brands do you carry?',
                        'Do you provide mobile tire services?',
                        'What are your operating hours?'
                    ])
                })
                
                # Some inquiries have follow-up dates
                if random.choice([True, False]):
                    order_data['follow_up_date'] = order_date.date() + timedelta(days=random.randint(1, 14))
            
            try:
                order = Order.objects.create(**order_data)
                orders_created += 1
                print(f"Created {order_type} order #{order.order_number} for {customer.full_name} - Status: {status}")
            except Exception as e:
                print(f"Error creating order for {customer.full_name}: {e}")
    
    print(f"\nSample data creation completed!")
    print(f"Created {len(brands)} brands")
    print(f"Created {len(inventory_items)} inventory items")
    print(f"Created {len(customers)} customers")
    print(f"Created {len(vehicles)} vehicles")
    print(f"Created {orders_created} orders")
    
    # Print summary statistics
    print(f"\nOrder Statistics:")
    for order_type in order_types:
        count = Order.objects.filter(type=order_type).count()
        print(f"  {order_type.title()}: {count}")
    
    print(f"\nStatus Statistics:")
    for status in statuses:
        count = Order.objects.filter(status=status).count()
        print(f"  {status.replace('_', ' ').title()}: {count}")

if __name__ == '__main__':
    create_sample_data()