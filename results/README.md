# Pipeline results

`venue_assignments.csv.gz` holds the venue IDs this pipeline has committed to the database: one row per location record, mapping `location_id` (→ `data/locations.csv.gz`) to a `venue_id` such as `WY-00012`.

| Column | Meaning |
|---|---|
| `location_id` | The listing (one edition's entry) |
| `venue_id` | The resolved venue, `{STATE}-{seq}`. Shared by every listing judged to be the same establishment |
| `group_size` | Number of listings in the venue |
| `confidence_score` | Lowest composite similarity score among the venue's matched pairs |
| `resolution_method` | `auto_match`, `ai_adjudicated`, `manual_edit`, or `singleton` |
| `flags` | Consolidation warnings, if any |
| `date_assigned` | When the state was committed |

States are added as they finish review. Re-export after each commit:

```bash
python3 assign_ids.py NY --commit
python3 db_snapshot.py export
```

Same format as [`../data/`](../data/README.md): gzipped CSV, `\N` for NULL, with `schema.sql` and `manifest.json`.
