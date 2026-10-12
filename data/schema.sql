CREATE TABLE unique_locations (
            id INTEGER PRIMARY KEY,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            city VARCHAR(100),
            state VARCHAR(50),
            address_precision VARCHAR(50) DEFAULT 'general',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE locations (
            id INTEGER PRIMARY KEY,
            unique_id VARCHAR(100) UNIQUE NOT NULL,
            title VARCHAR(500),
            description TEXT,
            street_address VARCHAR(500),
            city VARCHAR(100),
            state VARCHAR(50),
            year INTEGER,
            notes TEXT,
            full_address VARCHAR(500),
            latitude FLOAT,
            longitude FLOAT,
            geo_address VARCHAR(500),
            unclear_address VARCHAR(10),
            status VARCHAR(200),
            unique_location_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(unique_location_id) REFERENCES unique_locations(id)
        );

CREATE TABLE amenity_features (
            id INTEGER PRIMARY KEY,
            name VARCHAR(500) UNIQUE NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        , short_description VARCHAR(200), descriptive_name VARCHAR(200));

CREATE TABLE location_types (
            id INTEGER PRIMARY KEY,
            name VARCHAR(500) UNIQUE NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE location_amenity_assignments (
            id INTEGER PRIMARY KEY,
            location_id INTEGER NOT NULL,
            amenity_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id),
            FOREIGN KEY(amenity_id) REFERENCES amenity_features(id),
            UNIQUE(location_id, amenity_id)
        );

CREATE TABLE location_type_assignments (
            id INTEGER PRIMARY KEY,
            location_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id),
            FOREIGN KEY(type_id) REFERENCES location_types(id),
            UNIQUE(location_id, type_id)
        );
