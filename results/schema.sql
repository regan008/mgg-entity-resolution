CREATE TABLE venue_assignments (
                location_id INTEGER PRIMARY KEY,
                venue_id TEXT NOT NULL,
                group_size INTEGER,
                confidence_score REAL,
                resolution_method TEXT,
                flags TEXT,
                date_assigned TEXT,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );
