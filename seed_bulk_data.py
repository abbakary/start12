import os
import sys
import django
from datetime import datetime, timedelta
import random

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from tracker.models import Branch, Customer, Vehicle, Order, Brand, InventoryItem, Profile


def ensure_branches(count=20):
    print(f"Creating {count} branches and branch users (password=myuser123)")
    branches = []
    regions = ['Central', 'Northern', 'Eastern', 'Western', 'Kampala Metro']
    for i in range(1, count + 1):
        name = f"Branch {i}"
        code = f"B{i:02d}"
        region = random.choice(regions)
        branch, created = Branch.objects.get_or_create(name=name, defaults={'code': code, 'region': region, 'is_active': True})
        branches.append(branch)
        if created:
            print(f"  Created branch: {name} ({code})")
        # Create a user for the branch with password myuser123
        username = f"{name.replace(' ', '').lower()}"
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, password='myuser123')
            # Create profile and link branch
            Profile.objects.create(user=user, branch=branch)
            print(f"    Created user: {username} (password=myuser123)")
    return branches


def ensure_brands_and_inventory(min_items=20):
    print("Creating brands and inventory items...")
    brand_names = ['Michelin', 'Bridgestone', 'Goodyear', 'Continental', 'Pirelli', 'Dunlop', 'Hankook']
    tire_types = ['All Season', 'Summer', 'Winter', 'Performance', 'Off-Road']
    sizes = ['195/65R15', '205/55R16', '225/45R17', '235/40R18', '245/35R19']

    brands = []
    for bn in brand_names:
        brand, _ = Brand.objects.get_or_create(name=bn, defaults={'description': f'{bn} tires'})
        brands.append(brand)

    inventory_items = []
    # Create items per brand until we reach min_items
    while len(inventory_items) < min_items:
        brand = random.choice(brands)
        t = random.choice(tire_types)
        size = random.choice(sizes)
        name = f"{t} {size}"
        item, created = InventoryItem.objects.get_or_create(
            name=name, brand=brand,
            defaults={
                'quantity': random.randint(5, 200),
                'price': random.randint(60, 400),
                'cost_price': random.randint(30, 250),
                'reorder_level': random.randint(5, 20),
                'location': f"Rack {random.randint(1, 12)}"
            }
        )
        if item not in inventory_items:
            inventory_items.append(item)
            if created:
                print(f"  Created inventory: {brand.name} - {name}")
        # avoid infinite loops by breaking if many duplicates
        if len(inventory_items) > min_items * 2:
            break

    print(f"  Total inventory items: {len(inventory_items)}")
    return brands, inventory_items


def ensure_customers_and_vehicles(min_customers=20):
    print(f"Creating {min_customers} customers and vehicles")
    first_names = ['John','Sarah','Michael','David','Grace','Robert','Emily','James','Linda','Paul','Anna','Mark','Olivia','Daniel','Susan','Peter','Nora','Victor','Helen','Sam']
    last_names = ['Smith','Johnson','Brown','Wilson','Okello','Nakato','Kayiwa','Mugisha','Kato','Nsubuga']
    customers = []
    for i in range(min_customers):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        full = f"{fn} {ln}"
        phone = f"+25670{random.randint(1000000,9999999)}"
        email = f"{fn.lower()}.{ln.lower()}{random.randint(1,99)}@example.com"
        reg_days = random.randint(5, 365 * 2)
        reg_date = timezone.now() - timedelta(days=reg_days)
        customer, created = Customer.objects.get_or_create(
            phone=phone,
            defaults={
                'full_name': full,
                'email': email,
                'customer_type': random.choice(['personal','company','ngo','government']),
                'organization_name': None,
                'registration_date': reg_date,
                'address': f"Plot {random.randint(1,999)}, {random.choice(['Kampala','Entebbe','Jinja','Mbarara'])} Road"
            }
        )
        customers.append(customer)
        if created:
            print(f"  Created customer: {customer.full_name}")

    # Create vehicles: each gets 1-3 vehicles
    makes = ['Toyota','Nissan','Mitsubishi','Isuzu','Mercedes','Volvo']
    models = ['Camry','Corolla','Hilux','Prado','Canter','Actros','CRV','Civic']
    vtypes = ['sedan','suv','truck','van','bus']
    vehicles = []
    for c in customers:
        for _ in range(random.randint(1,3)):
            plate = f"U{random.choice(['A','B','C'])}{random.randint(100,999)}{random.choice(['A','B','C'])}"
            vehicle, created = Vehicle.objects.get_or_create(
                plate_number=plate,
                defaults={
                    'customer': c,
                    'make': random.choice(makes),
                    'model': random.choice(models),
                    'vehicle_type': random.choice(vtypes)
                }
            )
            vehicles.append(vehicle)
            if created:
                print(f"    Created vehicle {vehicle.plate_number} for {c.full_name}")

    return customers, vehicles


def ensure_orders(customers, vehicles, inventory_items, min_orders=20):
    print(f"Creating {min_orders} orders spread across time")
    order_types = ['service','sales','inquiry']
    statuses_all = ['created','in_progress','overdue','completed','cancelled']
    statuses_no_completed = ['created','in_progress','overdue','cancelled']
    priorities = ['low','medium','high','urgent']
    service_types = ['Oil Change','Brake Service','Tire Rotation','Engine Tune-up','Battery Replacement','Wheel Alignment']

    created_count = 0
    attempts = 0
    while created_count < min_orders and attempts < min_orders * 5:
        attempts += 1
        cust = random.choice(customers)
        vehicle = random.choice(vehicles) if vehicles else None
        otype = random.choice(order_types)

        # Choose status: if service or sales -> do NOT use completed
        if otype in ('service','sales'):
            status = random.choice(statuses_no_completed)
        else:
            status = random.choice(statuses_all)

        days_ago = random.randint(1, 365 * 1)  # within last year
        created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0,23), minutes=random.randint(0,59))

        data = {
            'customer': cust,
            'vehicle': vehicle,
            'type': otype,
            'status': status,
            'priority': random.choice(priorities),
            'created_at': created_at,
            'description': None,
        }

        if otype == 'service':
            svc = random.choice(service_types)
            data['description'] = f"{svc} for {vehicle.make if vehicle else 'vehicle'}"
            data['estimated_duration'] = random.randint(30, 480)
            if status == 'in_progress':
                data['started_at'] = created_at + timedelta(minutes=random.randint(10,120))
        elif otype == 'sales':
            item = random.choice(inventory_items)
            data.update({
                'item_name': item.name,
                'brand': item.brand.name if item.brand else None,
                'quantity': random.randint(1,6),
                'tire_type': None,
                'description': f"Sale of {item.name}"
            })
            if status == 'in_progress':
                data['started_at'] = created_at + timedelta(minutes=random.randint(10,120))
        else:  # inquiry
            data.update({
                'inquiry_type': random.choice(['Pricing','Appointment','Services','General']),
                'questions': 'Can I book an appointment?',
            })

        try:
            order = Order.objects.create(**data)
            created_count += 1
            print(f"  Created order {order.order_number} ({order.type}) for {cust.full_name} - status: {order.status}")
        except Exception as e:
            print(f"  Error creating order: {e}")

    print(f"  Total orders created: {created_count}")
    return created_count


if __name__ == '__main__':
    branches = ensure_branches(20)
    brands, inventory_items = ensure_brands_and_inventory(20)
    customers, vehicles = ensure_customers_and_vehicles(20)
    orders_created = ensure_orders(customers, vehicles, inventory_items, 30)

    print("\nSeeding completed. Summary:")
    print(f"  Branches: {Branch.objects.count()}")
    print(f"  Users: {User.objects.count()}")
    print(f"  Brands: {Brand.objects.count()}")
    print(f"  Inventory items: {InventoryItem.objects.count()}")
    print(f"  Customers: {Customer.objects.count()}")
    print(f"  Vehicles: {Vehicle.objects.count()}")
    print(f"  Orders: {Order.objects.count()}")
