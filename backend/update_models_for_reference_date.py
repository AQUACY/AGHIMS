#!/usr/bin/env python3
"""
Script to update all model files to use utcnow_callable instead of datetime.utcnow
This ensures all database timestamps use the APPLICATION_REFERENCE_DATE when configured.

Usage:
    python update_models_for_reference_date.py
"""

import os
import re
from pathlib import Path

# Directory containing model files
MODELS_DIR = Path("app/models")

# Pattern to find datetime.utcnow in default parameters
PATTERN = re.compile(r'default=datetime\.utcnow(?:,\s*onupdate=datetime\.utcnow)?')

def update_model_file(file_path):
    """Update a single model file to use utcnow_callable"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    updated = False
    
    # Check if file already imports utcnow_callable
    if 'from app.core.datetime_utils import utcnow_callable' not in content:
        # Add import after other imports
        if 'from app.core.database import Base' in content:
            content = content.replace(
                'from app.core.database import Base',
                'from app.core.database import Base\nfrom app.core.datetime_utils import utcnow_callable'
            )
            updated = True
        elif 'from datetime import datetime' in content:
            # Add after datetime import
            content = re.sub(
                r'(from datetime import datetime)',
                r'\1\nfrom app.core.datetime_utils import utcnow_callable',
                content,
                count=1
            )
            updated = True
    
    # Replace datetime.utcnow with utcnow_callable
    # Handle both default and onupdate
    content = re.sub(
        r'default=datetime\.utcnow(?:,\s*onupdate=datetime\.utcnow)?',
        lambda m: m.group(0).replace('datetime.utcnow', 'utcnow_callable'),
        content
    )
    
    # Also handle onupdate separately if it wasn't caught
    content = re.sub(
        r'onupdate=datetime\.utcnow',
        'onupdate=utcnow_callable',
        content
    )
    
    if content != original_content:
        updated = True
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, file_path
    
    return False, None

def main():
    """Main function to update all model files"""
    if not MODELS_DIR.exists():
        print(f"Error: Models directory not found: {MODELS_DIR}")
        return
    
    updated_files = []
    skipped_files = []
    
    # Get all Python files in models directory
    model_files = list(MODELS_DIR.glob("*.py"))
    
    # Exclude __init__.py
    model_files = [f for f in model_files if f.name != "__init__.py"]
    
    print(f"Found {len(model_files)} model files to check...")
    print()
    
    for model_file in sorted(model_files):
        print(f"Processing {model_file.name}...", end=" ")
        try:
            updated, file_path = update_model_file(model_file)
            if updated:
                updated_files.append(file_path)
                print("✓ Updated")
            else:
                skipped_files.append(model_file.name)
                print("- No changes needed")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Updated: {len(updated_files)} files")
    print(f"  Skipped: {len(skipped_files)} files")
    print()
    
    if updated_files:
        print("Updated files:")
        for f in updated_files:
            print(f"  - {f}")
        print()
        print("✓ All model files have been updated to use APPLICATION_REFERENCE_DATE")
        print()
        print("Next steps:")
        print("1. Review the changes")
        print("2. Test the application")
        print("3. Set APPLICATION_REFERENCE_DATE in your .env file")
    else:
        print("No files needed updating. All models may already be using utcnow_callable.")

if __name__ == "__main__":
    main()

