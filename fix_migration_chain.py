"""Script to fix Alembic migration chain dependencies."""

import os
import re
from pathlib import Path

# Define the correct migration chain based on timestamps and logical order
migration_chain = [
    ('20240210_initial_migration.py', '20240210_initial', None),  # Initial migration
    ('20240517_add_user_role.py', '20240517_add_user_role', '20240210_initial'),
    ('20240520_add_reservations_table.py', '20240520a', '20240517_add_user_role'),
    ('20240520_add_themes_tables.py', '20240520b', '20240520a'),
    ('20240520_add_side_quests_tables.py', '20240520c', '20240520b'),
    ('20240521_add_story_metadata.py', '20240521_metadata', '20240520c'),
    ('20240521_major_schema_update.py', '20240521_major', '20240521_metadata'),
    ('add_password_history_table.py', 'add_password_history', '20240521_major'),
    ('20250111_database_optimization_six_sigma.py', 'database_optimization_six_sigma', 'add_password_history'),
    ('20250123_add_event_journeys.py', '20250123_add_event_journeys', 'database_optimization_six_sigma'),
    ('add_performance_indexes.py', 'add_performance_indexes_old', '20250123_add_event_journeys'),
    ('20250523_add_commission_tracking.py', 'add_commission_tracking', 'add_performance_indexes_old'),
    ('20250527_add_parking_reservations.py', '20250527_add_parking_reservations', 'add_commission_tracking'),
    ('20250603_add_2fa_security_fields.py', '20250603_add_2fa_security_fields', '20250527_add_parking_reservations'),
    ('20250611_add_performance_indexes.py', 'add_performance_indexes', '20250603_add_2fa_security_fields'),
    ('20250711_api_keys_table.py', 'api_keys_001', 'add_performance_indexes'),
    ('002_add_journey_tracking_and_memories.py', '002_journey_tracking', 'api_keys_001'),
    ('20250130_add_progress_tracking_models.py', '20250130_progress_tracking', '002_journey_tracking'),
]

def fix_migration_file(filepath, new_down_revision):
    """Update the down_revision in a migration file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update down_revision
    if new_down_revision is None:
        new_content = re.sub(
            r"down_revision = ['\"].*?['\"]", 
            "down_revision = None", 
            content
        )
    else:
        new_content = re.sub(
            r"down_revision = .*", 
            f"down_revision = '{new_down_revision}'", 
            content
        )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Updated {filepath.name}: down_revision = {new_down_revision}")

def main():
    """Fix all migration dependencies."""
    migrations_dir = Path("alembic/versions")
    
    # Fix each migration
    for filename, revision_id, down_revision in migration_chain:
        filepath = migrations_dir / filename
        if filepath.exists():
            fix_migration_file(filepath, down_revision)
        else:
            print(f"Warning: {filename} not found")
    
    # Handle duplicate add_performance_indexes.py - rename the old one
    old_perf_indexes = migrations_dir / "add_performance_indexes.py"
    if old_perf_indexes.exists():
        # Read the file to update revision ID
        with open(old_perf_indexes, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update revision ID to avoid conflicts
        content = re.sub(
            r"revision = ['\"]add_performance_indexes['\"]",
            "revision = 'add_performance_indexes_old'",
            content
        )
        
        with open(old_perf_indexes, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Updated old add_performance_indexes.py revision ID to avoid conflicts")
    
    print("\nMigration chain fixed! Run 'alembic upgrade head' to apply all migrations.")

if __name__ == "__main__":
    main()