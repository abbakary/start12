#!/usr/bin/env python3
"""
Remove Timezone Display Script
==============================
This script removes timezone display from all templates
"""

import os
import re

def update_template_file(file_path):
    """Remove timezone display from a template file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove timezone display patterns
        patterns_to_remove = [
            r'\s*\({{ timezone }}\)',
            r'\s*<small class="text-muted">\({{ timezone }}\)</small>',
            r'\s*<span class="d-block text-muted">{{ timezone }}</span>',
            r'\s*\(Africa%2FDar_es_Salaam\)',
            r'\s*{{ timezone }}',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content)
        
        # Clean up any double spaces or empty lines
        content = re.sub(r'\s+', ' ', content)
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
    print("Removing timezone display from all templates...")
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
    print("Timezone display removal completed!")

if __name__ == '__main__':
    main()