#!/usr/bin/env python3
"""
Update Date Formats Script
==========================
This script updates all templates to use the new custom date format (Sep 22, 2025 10:38)
"""

import os
import re

def update_template_file(file_path):
    """Update a single template file with new date formats"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add date_filters load if not present
        if '{% load date_filters %}' not in content:
            # Find existing load statements
            load_pattern = r'({% load [^%]+%})'
            loads = re.findall(load_pattern, content)
            if loads:
                # Add after last load statement
                last_load = loads[-1]
                content = content.replace(last_load, last_load + '\n{% load date_filters %}')
            else:
                # Add after extends if present
                if '{% extends' in content:
                    content = re.sub(r'({% extends [^%]+%})', r'\1\n{% load date_filters %}', content)
        
        # Replace common date formats
        replacements = [
            # Standard Django date formats
            (r'\|date:"M d, Y H:i"', '|custom_date'),
            (r'\|date:"M d, Y"', '|custom_date_only'),
            (r'\|date:"Y-m-d H:i"', '|custom_date'),
            (r'\|date:"F j, Y"', '|custom_date_only'),
            (r'\|date:"j M Y"', '|custom_date_only'),
            (r'\|date:"M j, Y"', '|custom_date_only'),
            
            # With timezone
            (r'\|localtime\|date:"M d, Y H:i"', '|custom_date'),
            (r'\|localtime\|date:"M d, Y"', '|custom_date_only'),
            
            # Time only formats
            (r'\|time:"h:i A"', '|date:"H:i"'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        else:
            print(f"- No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all template files"""
    print("Updating date formats in all templates...")
    print("=" * 50)
    
    # Template directories to scan
    template_dirs = [
        'tracker/templates/tracker',
        'tracker/templates/registration'
    ]
    
    updated_count = 0
    total_count = 0
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        total_count += 1
                        if update_template_file(file_path):
                            updated_count += 1
    
    print("=" * 50)
    print(f"Summary: {updated_count}/{total_count} templates updated")
    print("Date format update completed!")
    
    print("\nManual updates needed:")
    print("1. Check order_detail.html for specific date displays")
    print("2. Check customers_list.html for table date columns")
    print("3. Check orders_list.html for table date columns")
    print("4. Verify dashboard.html recent orders section")

if __name__ == '__main__':
    main()