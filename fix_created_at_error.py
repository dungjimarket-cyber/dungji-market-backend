#!/usr/bin/env python
"""
Fix script to replace created_at with start_time in GroupBuy ordering
This fixes the FieldError in production
"""

import os
import re

def fix_created_at_in_file(filepath):
    """Replace created_at with start_time in order_by statements for GroupBuy"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace patterns
    patterns = [
        (r"queryset\.order_by\('-created_at'\)", "queryset.order_by('-start_time')"),
        (r"queryset\.order_by\('-current_participants', '-created_at'\)", "queryset.order_by('-current_participants', '-start_time')"),
        (r"order_by\('-created_at'\)", "order_by('-start_time')"),
        (r"order_by\('-current_participants', '-created_at'\)", "order_by('-current_participants', '-start_time')")
    ]
    
    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            print(f"Replaced: {pattern} -> {replacement}")
    
    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {filepath}")
        return True
    return False

def main():
    views_file = 'api/views.py'
    
    if os.path.exists(views_file):
        print(f"Checking {views_file}...")
        if fix_created_at_in_file(views_file):
            print("File has been fixed!")
        else:
            print("No changes needed or already fixed.")
    else:
        print(f"Error: {views_file} not found!")

if __name__ == "__main__":
    main()