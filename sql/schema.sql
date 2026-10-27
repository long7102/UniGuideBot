CREATE TABLE IF NOT EXISTS universities (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL, short_name TEXT NOT NULL UNIQUE,
 city TEXT NOT NULL, region TEXT NOT NULL CHECK(region IN ('bac','trung','nam')),
 website TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS university_fields (
 university_id INTEGER NOT NULL REFERENCES universities(id),
 field TEXT NOT NULL,
 PRIMARY KEY(university_id,field)
);
CREATE INDEX IF NOT EXISTS idx_region ON universities(region);
CREATE INDEX IF NOT EXISTS idx_field ON university_fields(field);
