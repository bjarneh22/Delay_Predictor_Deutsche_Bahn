import sqlite3
import os

# prepare sql statements to create the different tables
sql_statements = [

    # enforce foreign_keys and write-ahead logging
    "PRAGMA foreign_keys = ON;",

    "PRAGMA journal_mode =WAL;",

    """CREATE TABLE IF NOT EXISTS hist_train_delay(
            uid INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER,
            start_station_name TEXT,
            end_station_name TEXT,
            train_name TEXT,
            train_type TEXT,
            departure_planned TEXT,
            departure_actual TEXT,
            arrival_planned TEXT,
            arrival_actual TEXT,
            delay_in_min INTEGER
    );
    """,

    """CREATE TABLE IF NOT EXISTS stations(
            station_id TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL
    );
    """,

    """CREATE TABLE IF NOT EXISTS journeys(
            journey_id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_line TEXT,
            start_station_id TEXT,
            end_station_id TEXT,
            departure_time TEXT,
            planned_arrival_time TEXT,
            actual_arrival_time TEXT,
            delay_minutes REAL,
            collected_at TEXT NOT NULL,
            FOREIGN KEY(start_station_id) REFERENCES stations(station_id),
            FOREIGN KEY(end_station_id) REFERENCES stations(station_id)
    );
    """,

    """CREATE TABLE IF NOT EXISTS weather(
            weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT,
            temperature REAL,
            precipitation REAL,
            wind_speed REAL,
            collected_at TEXT NOT NULL,
            FOREIGN KEY(station_id) REFERENCES stations(station_id)
    );
    """,

    """CREATE INDEX IF NOT EXISTS ind_journeys_departure
        ON journeys(departure_time);    
    """,

    """CREATE INDEX IF NOT EXISTS ind_journeys_delay
        ON journeys(delay_minutes);    
    """,

    """CREATE INDEX IF NOT EXISTS ind_weather_station_time
        ON weather(station_id, collected_at);
    """
]

#resolving path issues
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "hist_train_delay.db")


try:
    with sqlite3.connect(DB_PATH) as conn:

        # create a cursor
        cursor = conn.cursor()

        # execute statements
        for statement in sql_statements:
            cursor.execute(statement)

        # commit the changes
        conn.commit()

        print("Tabellen wurden erstellt.")

except sqlite3.OperationalError as e:
    print("Tabllen wurden nicht erstellt:", e)


