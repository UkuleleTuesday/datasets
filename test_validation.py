#!/usr/bin/env python3
"""
Simple tests for dataset validation.
"""

import json
import tempfile
import os
import subprocess
import sys
from pathlib import Path


def test_song_sheets_validation():
    """Test song sheets validation with valid and invalid data."""
    print("Testing song-sheets validation...")
    
    # Test with valid data
    valid_data = [
        {
            "id": "test-123",
            "name": "Test Song - Test Artist",
            "properties": {
                "artist": "Test Artist",
                "song": "Test Song",
                "status": "APPROVED",
                "tabber": "Test Tabber",
                "bpm": "120",
                "chords": "C,G,Am,F",
                "date": "20240101",
                "difficulty": "2.5",
                "duration": "00:03:30",
                "gender": "male",
                "language": "english",
                "source": "new",
                "specialbooks": "regular",
                "time_signature": "4/4",
                "type": "Person",
                "year": "2020"
            }
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(valid_data, f)
        valid_file = f.name
    
    try:
        result = subprocess.run([
            sys.executable, 'validate_datasets.py',
            '--dataset', 'song-sheets',
            valid_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Valid song-sheets data passed validation")
        else:
            print("❌ Valid song-sheets data failed validation")
            print(result.stdout)
            print(result.stderr)
            return False
    finally:
        os.unlink(valid_file)
    
    # Test with invalid data (missing required field)
    invalid_data = [
        {
            "id": "test-123",
            "name": "Test Song - Test Artist",
            "properties": {
                "artist": "Test Artist",
                # Missing required "song" field
                "status": "APPROVED",
                "tabber": "Test Tabber"
            }
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        invalid_file = f.name
    
    try:
        result = subprocess.run([
            sys.executable, 'validate_datasets.py',
            '--dataset', 'song-sheets',
            invalid_file
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("✅ Invalid song-sheets data correctly failed validation")
            return True
        else:
            print("❌ Invalid song-sheets data incorrectly passed validation")
            return False
    finally:
        os.unlink(invalid_file)


def test_jam_sessions_validation():
    """Test jam sessions validation with valid and invalid data."""
    print("Testing jam-sessions validation...")
    
    # Test with valid data
    valid_data = [
        {
            "session_id": "test-session-1",
            "date": "2024-01-15",
            "venue": "Test Venue",
            "source_sheet": "Test Sheet",
            "ingested_at": "2024-01-15T10:30:00Z",
            "events": [
                {
                    "position": 1,
                    "type": "song",
                    "page": "42",
                    "song": "Test Song",
                    "artist": "Test Artist",
                    "requested_by_code": "A"
                }
            ],
            "requests": []
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for session in valid_data:
            f.write(json.dumps(session) + '\n')
        valid_file = f.name
    
    try:
        result = subprocess.run([
            sys.executable, 'validate_datasets.py',
            '--dataset', 'jam-sessions',
            valid_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Valid jam-sessions data passed validation")
            return True
        else:
            print("❌ Valid jam-sessions data failed validation")
            print(result.stdout)
            print(result.stderr)
            return False
    finally:
        os.unlink(valid_file)


def main():
    """Run all tests."""
    print("Running dataset validation tests...")
    print("="*50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_song_sheets_validation():
        tests_passed += 1
    
    if test_jam_sessions_validation():
        tests_passed += 1
    
    print("="*50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())