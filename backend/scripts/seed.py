#!/usr/bin/env python3
"""
Seed script to populate initial data into Supabase.
Run this after creating your Supabase project and running the schema.
"""
import os
import sys
from supabase import create_client

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("❌ Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars")
        sys.exit(1)
    
    supabase = create_client(url, key)
    
    # Create a sample pipeline configuration
    pipeline = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "name": "Test Pipeline",
        "niche": "tech",
        "theme_description": "Technology and startup content",
        "target_platforms": ["tiktok", "instagram"],
        "autonomy_mode": "suggestOnly",
        "status": "setup-incomplete",
        "max_clips_per_week": 21,
        "min_clip_length": 15,
        "max_clip_length": 90
    }
    
    try:
        result = supabase.table("pipelines").insert(pipeline).execute()
        print(f"✅ Created sample pipeline: {result.data[0]['id']}")
    except Exception as e:
        print(f"⚠️ Could not create sample pipeline: {e}")
    
    print("\n🎉 Seeding complete!")

if __name__ == "__main__":
    main()
