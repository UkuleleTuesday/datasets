#!/usr/bin/env python3
"""
Tests for the sanitization module.
"""
import sys
import pandas as pd
from sanitization import (
    normalize_for_matching,
    create_match_key,
    find_canonical_match,
    sanitize_jam_events,
)


def test_normalize_for_matching():
    """Test the normalization function."""
    print("Testing normalize_for_matching...")
    
    # Test basic normalization
    assert normalize_for_matching("  Hello World  ") == "hello world"
    assert normalize_for_matching("UPPERCASE") == "uppercase"
    assert normalize_for_matching("MiXeD CaSe") == "mixed case"
    assert normalize_for_matching("") == ""
    
    print("✅ normalize_for_matching tests passed")
    return True


def test_create_match_key():
    """Test the match key creation."""
    print("Testing create_match_key...")
    
    assert create_match_key("Song Name", "Artist Name") == "Song Name - Artist Name"
    assert create_match_key("", "") == " - "
    
    print("✅ create_match_key tests passed")
    return True


def test_find_canonical_match():
    """Test finding canonical matches."""
    print("Testing find_canonical_match...")
    
    canonical_songs = [
        {'id': 'id1', 'song': 'Wonderwall', 'artist': 'Oasis'},
        {'id': 'id2', 'song': 'Hotel California', 'artist': 'Eagles'},
        {'id': 'id3', 'song': 'Bohemian Rhapsody', 'artist': 'Queen'},
    ]
    
    # Test exact match (after normalization)
    result = find_canonical_match('wonderwall', 'oasis', canonical_songs)
    assert result is not None
    assert result['canonical_song'] == 'Wonderwall'
    assert result['canonical_artist'] == 'Oasis'
    assert result['matched_id'] == 'id1'
    assert result['match_score'] > 0.95
    
    # Test typo match
    result = find_canonical_match('Wonderwal', 'Oasis', canonical_songs)
    assert result is not None
    assert result['canonical_song'] == 'Wonderwall'
    assert result['canonical_artist'] == 'Oasis'
    
    # Test whitespace difference
    result = find_canonical_match('  Wonderwall  ', '  Oasis  ', canonical_songs)
    assert result is not None
    assert result['canonical_song'] == 'Wonderwall'
    
    # Test no match (very different)
    result = find_canonical_match('Completely Different Song', 'Unknown Artist', canonical_songs, threshold=0.8)
    assert result is None
    
    # Test match with lower threshold
    result = find_canonical_match('Hotel Californ', 'Eagles', canonical_songs, threshold=0.7)
    assert result is not None
    assert result['canonical_song'] == 'Hotel California'
    
    print("✅ find_canonical_match tests passed")
    return True


def test_sanitize_jam_events():
    """Test sanitizing a DataFrame of jam events."""
    print("Testing sanitize_jam_events...")
    
    # Create test data
    events_data = {
        'type': ['song', 'song', 'break', 'song', 'song'],
        'song': ['wonderwall', 'Hotel Californ', None, 'Bohemian Rhapsodie', 'Unknown Song'],
        'artist': ['oasis', 'Eagles', None, 'Queen', 'Unknown Artist'],
        'position': [1, 2, 3, 4, 5],
    }
    events_df = pd.DataFrame(events_data)
    
    canonical_songs = [
        {'id': 'id1', 'song': 'Wonderwall', 'artist': 'Oasis'},
        {'id': 'id2', 'song': 'Hotel California', 'artist': 'Eagles'},
        {'id': 'id3', 'song': 'Bohemian Rhapsody', 'artist': 'Queen'},
    ]
    
    # Sanitize the events
    sanitized_df, matches_log, unmatched = sanitize_jam_events(
        events_df, canonical_songs, threshold=0.7
    )
    
    # Check that song names were sanitized
    assert sanitized_df.at[0, 'song'] == 'Wonderwall'
    assert sanitized_df.at[0, 'artist'] == 'Oasis'
    assert sanitized_df.at[1, 'song'] == 'Hotel California'
    assert sanitized_df.at[1, 'artist'] == 'Eagles'
    assert sanitized_df.at[3, 'song'] == 'Bohemian Rhapsody'
    assert sanitized_df.at[3, 'artist'] == 'Queen'
    
    # Check that break event was not modified
    assert sanitized_df.at[2, 'type'] == 'break'
    
    # Check that unmatched song remains unchanged
    assert sanitized_df.at[4, 'song'] == 'Unknown Song'
    assert sanitized_df.at[4, 'artist'] == 'Unknown Artist'
    
    # Check matches log
    assert len(matches_log) == 3  # Three songs matched
    assert matches_log[0]['original_song'] == 'wonderwall'
    assert matches_log[0]['canonical_song'] == 'Wonderwall'
    
    # Check unmatched warnings
    assert len(unmatched) == 1
    assert unmatched[0]['song'] == 'Unknown Song'
    assert unmatched[0]['artist'] == 'Unknown Artist'
    
    print("✅ sanitize_jam_events tests passed")
    return True


def main():
    """Run all tests."""
    print("Running sanitization tests...")
    print("=" * 50)
    
    tests = [
        test_normalize_for_matching,
        test_create_match_key,
        test_find_canonical_match,
        test_sanitize_jam_events,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"❌ Test {test.__name__} failed: {e}")
        except Exception as e:
            print(f"💥 Test {test.__name__} errored: {e}")
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All sanitization tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
