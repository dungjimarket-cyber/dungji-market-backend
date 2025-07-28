#!/usr/bin/env python
"""
Script to check GroupBuy model fields and verify start_time exists
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_groupbuy import GroupBuy

def check_fields():
    # Get all field names
    fields = [f.name for f in GroupBuy._meta.get_fields()]
    
    print("GroupBuy model fields:")
    for field in sorted(fields):
        print(f"  - {field}")
    
    # Check specific fields
    print("\nChecking for time-related fields:")
    time_fields = [f for f in fields if 'time' in f or 'created' in f or 'date' in f]
    for field in time_fields:
        print(f"  - {field}")
    
    # Check if created_at exists
    if 'created_at' in fields:
        print("\nWARNING: 'created_at' field exists")
    else:
        print("\n'created_at' field does NOT exist (this is correct)")
    
    # Check if start_time exists
    if 'start_time' in fields:
        print("'start_time' field exists (this is correct)")
    else:
        print("WARNING: 'start_time' field does NOT exist")

if __name__ == "__main__":
    check_fields()