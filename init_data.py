#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from tracker.models import Brand, Customer, Order, Vehicle, InventoryItem
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

def create_admin_user():
    """Create admin user if it doesn't exist"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✓ Admin user created: username='admin', password='admin123'")
    else:
        print("✓ Admin user already exists")

def create_brands():
    """Create sample brands"""
    brands = [
        {"name": "Michelin", "description": "Premium tires for all vehicles"},
        {"name": "Bridgestone", "description": "High-performance tires"},
        {"name": "Goodyear", "description": "Quality tires for all seasons"},
        {"name": "Pirelli", "description": "Luxury and performance tires"},
        {"name": "Dunlop", "description": "Reliable tires for everyday use"},
    ]
    
    brand_objects = []
    for brand_data in brands:
        brand, created = Brand.objects.get_or_create(
            name=brand_data["name"],
            defaults={"description": brand_data["description"]}
        )
        brand_objects.append(brand)
        print(f"✓ Created brand: {brand.name}")
    return brand_objects

def create_inventory_items(brands):
    """Create sample inventory items"""
    items = [
        {"name": "Tyre 185/65 R15", "description": "Passenger car tyre"},
        {"name": "Tyre 205/55 R16", "description": "Sedan tyre"},
        {"name": "Tyre 225/45 R17", "description": "Sports car tyre"},
        {"name": "Tyre 265/70 R16", "description": "SUV tyre"},
        {"name": "Tyre 31x10.5 R15", "description": "4x4 tyre"},
        {"name": "Tyre Tube", "description": "Inner tube for tubed tyres"},
        {"name": "Tyre Valve", "description": "Tyre valve stem"},
        {"name": "Wheel Balance Weights", "description": "For wheel balancing"},
    ]
    
    for item_data in items:
        brand = random.choice(brands)
        _, created = InventoryItem.objects.get_or_create(
            name=item_data["name"],
            brand=brand,
            defaults={
                "description": item_data["description"],
                "quantity": random.randint(0, 100),
                "price": round(random.uniform(5000, 50000), 2),
                "cost_price": round(random.uniform(4000, 45000), 2),
                "sku": f"SKU{random.randint(1000, 9999)}",
                "barcode": f"{random.randint(100000000000, 999999999999)}",
                "reorder_level": random.randint(5, 20),
                "location": f"Aisle {random.randint(1, 10)}, Shelf {random.choice('ABCDE')}",
                "is_active": random.choice([True, True, True, False])
            }
        )
        if created:
            print(f"✓ Created inventory item: {brand.name} - {item_data['name']}")

def create_customers():
    """Create sample customers"""
    customers_data = [
        {'full_name': 'John Doe', 'phone': '+255701234567', 'email': 'john@example.com', 'customer_type': 'personal'},
        {'full_name': 'Jane Smith', 'phone': '+255702345678', 'email': 'jane@example.com', 'customer_type': 'personal'},
        {'full_name': 'Robert Johnson', 'phone': '+255703456789', 'email': 'robert@example.com', 'customer_type': 'personal'},
        {'full_name': 'Emily Davis', 'phone': '+255704567890', 'email': 'emily@example.com', 'customer_type': 'personal'},
        {'full_name': 'Michael Brown', 'phone': '+255705678901', 'email': 'michael@example.com', 'customer_type': 'personal'},
        {'full_name': 'ABC Company Ltd', 'phone': '+255706789012', 'email': 'info@abc.com', 'customer_type': 'company', 'organization_name': 'ABC Company Ltd', 'tax_number': 'TIN12345'},
    ]
    
    customers = []
    for data in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=data['phone'],
            defaults=data
        )
        if created:
            customers.append(customer)
            print(f"✓ Created customer: {customer.full_name}")
    return customers

def create_vehicles(customers):
    """Create sample vehicles for customers"""
    vehicles_data = [
        {'make': 'Toyota', 'model': 'Corolla', 'vehicle_type': 'Sedan'},
        {'make': 'Nissan', 'model': 'Sunny', 'vehicle_type': 'Sedan'},
        {'make': 'Mitsubishi', 'model': 'Lancer', 'vehicle_type': 'Sedan'},
        {'make': 'Toyota', 'model': 'Hilux', 'vehicle_type': 'Pickup'},
        {'make': 'Nissan', 'model': 'Navara', 'vehicle_type': 'Pickup'},
        {'make': 'Toyota', 'model': 'Land Cruiser', 'vehicle_type': 'SUV'},
    ]
    
    vehicles = []
    for customer in customers:
        vehicle_data = random.choice(vehicles_data)
        plate_prefix = random.choice(['T', 'U', 'E'])
        plate_number = f"{plate_prefix}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')} {random.randint(100, 999)}"
        
        vehicle = Vehicle.objects.create(
            customer=customer,
            plate_number=plate_number,
            **vehicle_data
        )
        vehicles.append(vehicle)
        print(f"✓ Created vehicle: {vehicle.plate_number} - {vehicle.make} {vehicle.model}")
    return vehicles

def create_orders(customers, vehicles):
    """Create sample orders"""
    for i, customer in enumerate(customers):
        # Each customer gets 1-3 vehicles
        customer_vehicles = random.sample(vehicles, min(random.randint(1, 3), len(vehicles)))
        
        for vehicle in customer_vehicles:
            # Each vehicle gets 1-5 orders
            for _ in range(random.randint(1, 5)):
                # Get a random inventory item
                inventory_item = random.choice(InventoryItem.objects.all())
                
                order = Order.objects.create(
                    customer=customer,
                    vehicle=vehicle,
                    type=random.choice(["service", "sales"]),
                    status=random.choice(["created", "in_progress", "completed"]),
                    priority=random.choice(["low", "medium", "high"]),
                    description=f"Order for {vehicle.make} {vehicle.model} - {inventory_item.name}",
                    item_name=inventory_item.name,
                    brand=inventory_item.brand.name,
                    quantity=random.randint(1, 5),
                    tire_type=random.choice(["Tubeless", "Tube Type", "Radial"]),
                    price=inventory_item.price
                )
                
                # Update order timestamps to be within last 30 days
                order.created_at = timezone.now() - timedelta(days=random.randint(1, 30))
                if order.status == 'completed':
                    order.completed_at = order.created_at + timedelta(hours=random.randint(1, 24))
                order.save()
                
                # Update inventory quantity
                inventory_item.quantity = max(0, inventory_item.quantity - order.quantity)
                inventory_item.save()
                
                print(f"✓ Created order #{order.id} for {customer.full_name}")

def create_sample_data():
    """Create sample data for the application"""
    print("\nCreating brands...")
    brands = create_brands()
    
    print("\nCreating inventory items...")
    create_inventory_items(brands)
    
    print("\nCreating customers...")
    customers = create_customers()
    
    print("\nCreating vehicles...")
    vehicles = create_vehicles(customers)
    
    print("\nCreating orders...")
    create_orders(customers, vehicles)

if __name__ == '__main__':
    print("Initializing data...")
    create_admin_user()
    create_sample_data()
    print("\n🎉 Initialization complete!")
    print("You can now login with:")
    print("Username: admin")
    print("Password: admin123")
