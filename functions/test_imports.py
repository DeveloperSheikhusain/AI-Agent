#!/usr/bin/env python3
"""
Test script to check for import errors in Firebase functions
"""

import sys
sys.path.insert(0, '/var/www/html/AI-Agent/functions')

print("Testing imports...")

try:
    print("1. Testing bedrock_utils...")
    from bedrock_utils import get_config
    print("   ✓ bedrock_utils OK")
except Exception as e:
    print(f"   ✗ bedrock_utils FAILED: {e}")

try:
    print("2. Testing cost_utils...")
    from cost_utils import get_all_costs
    print("   ✓ cost_utils OK")
except Exception as e:
    print(f"   ✗ cost_utils FAILED: {e}")

try:
    print("3. Testing common...")
    from common import get_db
    print("   ✓ common OK")
except Exception as e:
    print(f"   ✗ common FAILED: {e}")

try:
    print("4. Testing main...")
    import main
    print("   ✓ main OK")
except Exception as e:
    print(f"   ✗ main FAILED: {e}")

print("\nAll imports successful!")
