# MGG source data

A complete, lossless snapshot of the [Mapping the Gay Guides](https://www.mappingthegayguides.org/) database tables this pipeline reads: 181,741 location records transcribed from Bob Damron's Address Books (1965–2003), with their amenity and venue-type tags.

These files replace the SQLite database (`mgg.db`) in version control. Rebuild it with:

```bash
python3 db_snapshot.py build
```

`python3 db_snapshot.py verify` rebuilds the database in a temporary directory and checks that every row, value, and value type matches the live `mgg.db`.

## Tables

| File | Rows | Contents |
|---|---|---|
| `locations.csv.gz` | 181,741 | One row per listing per edition: title, address, city, state, year, coordinates, description, notes |
| `location_amenity_assignments.csv.gz` | 287,357 | Listing ↔ amenity tag (Damron's codes, e.g. `(AYOR-1977-2005)`). `amenity_id = 90` is "Cruisy Area" |
| `location_type_assignments.csv.gz` | 191,826 | Listing ↔ venue type |
| `unique_locations.csv.gz` | 42,270 | An earlier grouping of listings by **shared geocoded coordinates** (`locations.unique_location_id`). It groups by place, not business, so it serves as a coordinate-only baseline to compare against this pipeline's venue IDs |
| `amenity_features.csv.gz` | 75 | Amenity code definitions |
| `location_types.csv.gz` | 70 | Venue type definitions |

`schema.sql` holds the exact `CREATE TABLE` statements. `manifest.json` records each file's row count, columns, and SHA-256. The build checks both.

**Not included:** `split_logging` and `split_location_details`, an audit trail of a one-time August 2025 cleanup that split amenity codes into era-specific versions. The pipeline doesn't read them.

## Format

- UTF-8 CSV with a header row, rows in primary-key order, gzip-compressed.
- **NULL is written as `\N`**, distinct from an empty field (`""`). Both occur: text columns use empty strings (e.g. 49,850 listings have no street address), while coordinates and foreign keys use NULL.
- Floats use Python's shortest round-trip representation, so coordinates reload bit-for-bit.
- Gzip headers carry no timestamp, so re-exporting unchanged data produces byte-identical files, and `git diff` shows only real data changes.

The pipeline's output (`venue_assignments`) is kept separately in [`../results/`](../results/).
