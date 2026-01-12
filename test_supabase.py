#!/usr/bin/env python3
"""
Test Supabase connection and credentials
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv('.env')

# Get credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

print("=== Supabase Connection Test ===")
print(f"SUPABASE_URL found: {'✅' if supabase_url else '❌'}")
print(f"SUPABASE_SERVICE_KEY found: {'✅' if supabase_key else '❌'}")

if supabase_url:
    print(f"URL: {supabase_url[:50]}...")

if supabase_key:
    print(f"Key length: {len(supabase_key)} characters")
    print(f"Key starts with: {supabase_key[:20]}...")

# Test connection
if supabase_url and supabase_key:
    print("\n=== Testing Connection ===")
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Test basic query
        result = supabase.table("executions").select("count").execute()
        print("✅ Supabase connection successful!")
        print(f"Executions table accessible: {'✅' if result else '❌'}")
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("\nPossible issues:")
        print("1. Invalid SUPABASE_URL")
        print("2. Invalid SUPABASE_SERVICE_KEY") 
        print("3. 'executions' table doesn't exist")
        print("4. Network connectivity issues")
else:
    print("\n❌ Cannot test connection - missing credentials")
