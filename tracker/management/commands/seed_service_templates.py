"""
Management command to seed default ServiceTemplate and InvoicePatternMatcher data.
Usage: python manage.py seed_service_templates
"""

from django.core.management.base import BaseCommand
from tracker.models import ServiceTemplate, InvoicePatternMatcher


class Command(BaseCommand):
    help = 'Seed default service templates and invoice pattern matchers'

    def handle(self, *args, **options):
        self.stdout.write('Seeding service templates and patterns...')
        
        # Common service templates for car service
        service_templates = [
            {
                'name': 'Oil Change',
                'keywords': 'oil change, oil service, oil replacement, oil top up',
                'estimated_minutes': 30,
                'service_type': 'service',
                'is_common': True,
            },
            {
                'name': 'Tire Rotation',
                'keywords': 'tire rotation, tyre rotation, wheel alignment, tire balance',
                'estimated_minutes': 45,
                'service_type': 'service',
                'is_common': True,
            },
            {
                'name': 'Brake Service',
                'keywords': 'brake, brake pads, brake fluid, brake service, brake check',
                'estimated_minutes': 60,
                'service_type': 'service',
                'is_common': True,
            },
            {
                'name': 'Air Filter Replacement',
                'keywords': 'air filter, air filter replacement, cabin filter',
                'estimated_minutes': 20,
                'service_type': 'service',
                'is_common': True,
            },
            {
                'name': 'Battery Service',
                'keywords': 'battery, battery replacement, battery service, battery check',
                'estimated_minutes': 30,
                'service_type': 'service',
                'is_common': True,
            },
            {
                'name': 'Tire Installation',
                'keywords': 'tire installation, tyre installation, tire mount, tyre mount, install tires',
                'estimated_minutes': 60,
                'service_type': 'sales',
                'is_common': True,
            },
            {
                'name': 'Tire Balancing',
                'keywords': 'balancing, balance, wheel balance, tire balance',
                'estimated_minutes': 30,
                'service_type': 'sales',
                'is_common': True,
            },
            {
                'name': 'General Maintenance',
                'keywords': 'maintenance, service, check, inspection, diagnostic',
                'estimated_minutes': 45,
                'service_type': 'service',
                'is_common': False,
            },
        ]
        
        created_count = 0
        for template_data in service_templates:
            template, created = ServiceTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults={
                    'keywords': template_data['keywords'],
                    'estimated_minutes': template_data['estimated_minutes'],
                    'service_type': template_data['service_type'],
                    'is_common': template_data['is_common'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {template.name}'))
                created_count += 1
            else:
                self.stdout.write(f'  → Already exists: {template.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nService Templates: {created_count} created'))
        
        # Common invoice patterns
        invoice_patterns = [
            {
                'name': 'Plate in reference field',
                'field_type': 'plate_number',
                'regex_pattern': r'(?:REFERENCE|REF|Plate|License|plate|reference)[\s:]*([A-Z]{3}\s?[A-Z]?\s?\d+\s?[A-Z]{2,3})',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Total amount with label',
                'field_type': 'amount',
                'regex_pattern': r'(?:Total|TOTAL|Amount|AMOUNT|Due|DUE)[\s:]*([A-Z])?[\s]*([\d,]+\.?\d{0,2})',
                'extract_group': 2,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Tanzania phone format',
                'field_type': 'customer_phone',
                'regex_pattern': r'(?:Phone|Tel|Mobile|Contact|phone|tel)[\s:]*(\+?255\s?\d{3}\s?\d{3}\s?\d{3}|0[67]\d{2}\s?\d{3}\s?\d{3})',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Customer name after label',
                'field_type': 'customer_name',
                'regex_pattern': r'(?:CUSTOMER|Customer|Name|name)[\s:]*([A-Za-z\s]+?)(?:\n|$|Phone|phone|Tel|tel|Address|address)',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Email pattern',
                'field_type': 'customer_email',
                'regex_pattern': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                'extract_group': 1,
                'priority': 10,
                'is_default': False,
            },
            {
                'name': 'Service/Item description',
                'field_type': 'service_description',
                'regex_pattern': r'(?:SERVICE|Service|Description|Item|ITEM|item|description)[\s:]*([A-Za-z0-9\s,.-]+?)(?:\n|Qty|Quantity|qty|$)',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Quantity field',
                'field_type': 'quantity',
                'regex_pattern': r'(?:QTY|Quantity|Qty|qty)[\s:]*(\d+)',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'Invoice/Reference number',
                'field_type': 'reference',
                'regex_pattern': r'(?:REF|Reference|Invoice|INV|reference|invoice|inv)[\s#:]*([A-Z0-9-]+)',
                'extract_group': 1,
                'priority': 10,
                'is_default': True,
            },
        ]
        
        created_count = 0
        for pattern_data in invoice_patterns:
            pattern, created = InvoicePatternMatcher.objects.get_or_create(
                name=pattern_data['name'],
                defaults={
                    'field_type': pattern_data['field_type'],
                    'regex_pattern': pattern_data['regex_pattern'],
                    'extract_group': pattern_data['extract_group'],
                    'priority': pattern_data['priority'],
                    'is_default': pattern_data['is_default'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {pattern.name}'))
                created_count += 1
            else:
                self.stdout.write(f'  → Already exists: {pattern.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nInvoice Patterns: {created_count} created'))
        self.stdout.write(self.style.SUCCESS('\n✓ Seeding complete! Service templates and patterns are ready to use.'))
