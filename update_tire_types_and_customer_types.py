#!/usr/bin/env python3
"""
Update Tire Types and Customer Types Script
==========================================
This script removes used/refurbished tire types and bodaboda customer type from all templates
"""

import os
import re

def update_template_file(file_path):
    """Update a single template file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove used and refurbished tire type options
        tire_patterns = [
            r'<option value="Used">Used</option>',
            r'<option value="Refurbished">Refurbished</option>',
            r'<option value="used">Used</option>',
            r'<option value="refurbished">Refurbished</option>',
        ]
        
        for pattern in tire_patterns:
            content = re.sub(pattern, '', content)
        
        # Remove bodaboda customer type options
        bodaboda_patterns = [
            r'<option value="bodaboda"[^>]*>Bodaboda</option>',
            r'<option value="bodaboda"[^>]*>.*?</option>',
        ]
        
        for pattern in bodaboda_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up any extra whitespace
        content = re.sub(r'\n\s*\n', '\n', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        else:
            print(f"No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all template files"""
    print("Updating tire types and customer types...")
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
    print("Update completed!")

if __name__ == '__main__':
    main()