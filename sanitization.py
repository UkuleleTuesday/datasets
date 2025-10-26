"""
Utilities for sanitizing jam session data using canonical song sheets.
"""
import difflib
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple


def normalize_for_matching(text: str) -> str:
    """
    Normalize a string for comparison by trimming whitespace and converting to lowercase.
    
    This function is intentionally kept minimal but structured to allow future extensions
    (e.g., removing punctuation, handling 'feat.' artists, etc.).
    
    Args:
        text: The string to normalize
        
    Returns:
        Normalized string (trimmed and lowercased)
    """
    return text.strip().lower()


def create_match_key(song: str, artist: str) -> str:
    """
    Create a combined 'song - artist' key for matching.
    
    Args:
        song: Song title
        artist: Artist name
        
    Returns:
        Combined key in format 'song - artist'
    """
    return f"{song} - {artist}"


def find_canonical_match(
    jam_song: str,
    jam_artist: str,
    canonical_songs: List[Dict[str, Any]],
    threshold: float = 0.8,
) -> Optional[Dict[str, Any]]:
    """
    Find a canonical song/artist match for a jam session entry using fuzzy matching.
    
    Args:
        jam_song: Song title from jam session
        jam_artist: Artist name from jam session
        canonical_songs: List of canonical song dictionaries with 'song', 'artist', and 'id'
        threshold: Minimum similarity score (0.0 to 1.0) for a match to be accepted
        
    Returns:
        Dictionary with match information if found, None otherwise.
        Match dict contains:
        - 'canonical_song': matched canonical song title
        - 'canonical_artist': matched canonical artist name
        - 'match_score': similarity score (0.0 to 1.0)
        - 'matched_id': ID of the matched song sheet
        - 'original_song': original jam session song title
        - 'original_artist': original jam session artist name
    """
    # Create the search key for the jam session entry
    jam_key = create_match_key(jam_song, jam_artist)
    jam_key_normalized = normalize_for_matching(jam_key)
    
    # Build a list of canonical keys and their normalized versions
    canonical_keys = []
    canonical_normalized_keys = []
    
    for song_data in canonical_songs:
        canonical_key = create_match_key(song_data['song'], song_data['artist'])
        canonical_keys.append(canonical_key)
        canonical_normalized_keys.append(normalize_for_matching(canonical_key))
    
    # Use difflib to find close matches
    matches = difflib.get_close_matches(
        jam_key_normalized,
        canonical_normalized_keys,
        n=1,  # We only want the best match
        cutoff=threshold
    )
    
    if not matches:
        return None
    
    # Find the index of the best match
    best_match_normalized = matches[0]
    match_index = canonical_normalized_keys.index(best_match_normalized)
    
    # Get the matched song data
    matched_song_data = canonical_songs[match_index]
    
    # Calculate the actual similarity score
    # Use SequenceMatcher to get precise score
    matcher = difflib.SequenceMatcher(None, jam_key_normalized, best_match_normalized)
    score = matcher.ratio()
    
    return {
        'canonical_song': matched_song_data['song'],
        'canonical_artist': matched_song_data['artist'],
        'match_score': score,
        'matched_id': matched_song_data['id'],
        'original_song': jam_song,
        'original_artist': jam_artist,
    }


def sanitize_jam_events(
    events_df,
    canonical_songs: List[Dict[str, Any]],
    threshold: float = 0.8,
) -> Tuple[Any, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Sanitize jam session events by matching to canonical song sheets.
    
    Args:
        events_df: DataFrame with jam session events (must have 'song' and 'artist' columns)
        canonical_songs: List of canonical song dictionaries
        threshold: Minimum similarity score for matching
        
    Returns:
        Tuple of (sanitized_df, matches_log, unmatched_warnings)
        - sanitized_df: DataFrame with sanitized song and artist names
        - matches_log: List of match information dictionaries
        - unmatched_warnings: List of unmatched entries
    """
    # Helper to safely convert to string
    safe_str = lambda x: '' if pd.isna(x) else x
    
    # Create a copy to avoid modifying the original
    sanitized_df = events_df.copy()
    matches_log = []
    unmatched_warnings = []
    
    # Only process song events
    song_mask = sanitized_df['type'] == 'song'
    
    for idx in sanitized_df[song_mask].index:
        jam_song = sanitized_df.at[idx, 'song']
        jam_artist = sanitized_df.at[idx, 'artist']
        
        # Skip if song or artist is None or NaN
        if pd.isna(jam_song) or pd.isna(jam_artist):
            unmatched_warnings.append({
                'song': safe_str(jam_song),
                'artist': safe_str(jam_artist),
                'key': create_match_key(safe_str(jam_song), safe_str(jam_artist))
            })
            continue
        
        # Try to find a canonical match
        match_result = find_canonical_match(
            jam_song, jam_artist, canonical_songs, threshold
        )
        
        if match_result:
            # Replace with canonical names
            sanitized_df.at[idx, 'song'] = match_result['canonical_song']
            sanitized_df.at[idx, 'artist'] = match_result['canonical_artist']
            matches_log.append(match_result)
        else:
            # Log unmatched entry
            unmatched_warnings.append({
                'song': jam_song,
                'artist': jam_artist,
                'key': create_match_key(jam_song, jam_artist)
            })
    
    return sanitized_df, matches_log, unmatched_warnings
