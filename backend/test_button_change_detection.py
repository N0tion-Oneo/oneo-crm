#!/usr/bin/env python3
"""
Test button field change detection logic
This isolates the change detection issue from the full Django context
"""

import json
from datetime import datetime

def test_button_change_detection():
    """Test if button field changes are detected properly"""
    
    # Simulate old button state (never clicked)
    old_button_state = {
        "type": "button",
        "triggered": False,
        "last_triggered": None,
        "click_count": 0,
        "config": {
            "help_text": None,
            "button_text": "Generate AI Summary",
            "button_style": "primary",
            "button_size": "medium",
            "workflow_id": None,
            "workflow_params": {},
            "require_confirmation": False,
            "confirmation_message": "Are you sure?",
            "disable_after_click": False,
            "visible_to_roles": [],
            "clickable_by_roles": []
        }
    }
    
    # Simulate new button state (clicked)
    new_button_state = {
        "type": "button",
        "triggered": True,
        "last_triggered": "2025-08-09T16:23:30.123Z",
        "click_count": 1,
        "config": {
            "help_text": None,
            "button_text": "Generate AI Summary",
            "button_style": "primary", 
            "button_size": "medium",
            "workflow_id": None,
            "workflow_params": {},
            "require_confirmation": False,
            "confirmation_message": "Are you sure?",
            "disable_after_click": False,
            "visible_to_roles": [],
            "clickable_by_roles": []
        }
    }
    
    # Test direct comparison
    print("=== BUTTON CHANGE DETECTION TEST ===")
    print(f"Old state: {old_button_state}")
    print(f"New state: {new_button_state}")
    print(f"Are they equal? {old_button_state == new_button_state}")
    print(f"Are they different? {old_button_state != new_button_state}")
    
    # Test key differences
    print("\n=== FIELD BY FIELD COMPARISON ===")
    for key in set(old_button_state.keys()) | set(new_button_state.keys()):
        old_val = old_button_state.get(key)
        new_val = new_button_state.get(key) 
        changed = old_val != new_val
        print(f"  {key}: {old_val} -> {new_val} (changed: {changed})")
        
        if key == 'config' and changed:
            print("    Config differences:")
            for config_key in set(old_val.keys()) | set(new_val.keys()):
                old_config = old_val.get(config_key)
                new_config = new_val.get(config_key)
                config_changed = old_config != new_config
                if config_changed:
                    print(f"      {config_key}: {old_config} -> {new_config}")
    
    # Test simulated record data comparison
    print("\n=== RECORD DATA COMPARISON ===")
    old_data = {
        "name": "Test Record",
        "ai_summary_trigger": old_button_state,
        "other_field": "unchanged"
    }
    
    new_data = {
        "name": "Test Record", 
        "ai_summary_trigger": new_button_state,
        "other_field": "unchanged"
    }
    
    changed_fields = []
    for field_slug in set(old_data.keys()) | set(new_data.keys()):
        old_value = old_data.get(field_slug)
        new_value = new_data.get(field_slug)
        
        print(f"Field '{field_slug}':")
        print(f"  Old: {old_value}")
        print(f"  New: {new_value}")
        print(f"  Equal: {old_value == new_value}")
        print(f"  Types: {type(old_value)} vs {type(new_value)}")
        
        if old_value != new_value:
            print(f"  ✅ CHANGED: Adding '{field_slug}' to changed fields")
            changed_fields.append(field_slug)
        else:
            print(f"  ❌ NO CHANGE: Field '{field_slug}' unchanged")
        print()
    
    print(f"Final changed fields: {changed_fields}")
    
    # Expected result: ai_summary_trigger should be in changed_fields
    expected = ['ai_summary_trigger']
    success = changed_fields == expected
    print(f"\n=== TEST RESULT ===")
    print(f"Expected: {expected}")
    print(f"Actual: {changed_fields}")
    print(f"SUCCESS: {success}")
    
    return success

if __name__ == "__main__":
    test_button_change_detection()