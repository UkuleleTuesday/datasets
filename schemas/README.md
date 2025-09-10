# Dataset Schemas

This directory contains JSON schemas for validating Ukulele Tuesday datasets.

## Schemas

### `sessions.json`
JSON Schema for jam sessions dataset. Each session contains:
- Session metadata (ID, date, venue, source)
- Array of events (songs, breaks, notes)
- Array of requests (currently empty but reserved for future use)

**Events Types:**
- `song`: Requires `song` and `artist` fields
- `break`: No additional fields required
- `note`: Requires `label` field

### `song-sheets.json`
JSON Schema for song sheets dataset. This is an array of song objects, each containing:
- `id`: Unique identifier
- `name`: Display name
- `properties`: Song metadata including artist, difficulty, chords, etc.

**Status Values:** `APPROVED`, `READY_TO_PLAY`
**Source Values:** `new`, `old`, `off`
**Gender Values:** `male`, `female`, `duet`, `ensemble`, `instrumental`
**Type Values:** `Person`, `Group`, `person`, `group`

## Validation

Use the `validate_datasets.py` script to validate datasets against these schemas:

```bash
# Validate all datasets
python validate_datasets.py --dataset all

# Validate specific dataset
python validate_datasets.py --dataset song-sheets
python validate_datasets.py --dataset jam-sessions

# Use custom file paths
python validate_datasets.py --dataset song-sheets --song-sheets-file /path/to/data.json
```

The validation is automatically run as part of the CI pipeline when datasets are generated.

## Testing

Run `test_validation.py` to test the validation system with sample data.