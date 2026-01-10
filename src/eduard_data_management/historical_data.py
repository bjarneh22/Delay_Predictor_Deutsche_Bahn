from datasets import load_dataset
import sqlite3
import csv
import os

# Load the huggingface dataset and load it into the train_delay.csv
ds = load_dataset(
    "piebro/deutsche-bahn-data",
    split="train",
    streaming=True
)

# opens the csv file and writes the header
with open("train_delay.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "id", "start_station_name", "end_station_name",
        "train_name", "train_type",
        "departure_planned", "departure_actual",
        "arrival_planned", "arrival_actual", "delay_in_min", "is_canceled"
    ])

    BATCH_SIZE = 1000 #to add a counter to the process
    counter = 0

#takes the huggingface dataset row for row and inserts the rows that match the if condition and puts the specific value in its column
    for row in ds:
        if row["train_type"] in {"ICE","IC","EC","ECE","RJ","RJX","FLX","NJ"}:
            writer.writerow([
                row["eva"],
                row["station_name"],
                row["final_destination_station"],
                row["train_name"],
                row["train_type"],
                row["departure_planned_time"],
                row["departure_change_time"],
                row["arrival_planned_time"],
                row["arrival_change_time"],
                row["delay_in_min"],
                row["is_canceled"]
            ])

            counter += 1

            if counter % BATCH_SIZE == 0:
                print(f"Commited {counter} rows")


#read csv and import into db
with open("train_delay.csv", newline = "", encoding = "utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)

    #adding another counter just to make sure
    counter_sql = 0

    # resolving path issues (important to take a look at that to see that DB_PATH matches the directory of the hist_train_delay.db)
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")
    DB_PATH = os.path.join(DATA_DIR, "hist_train_delay.db")

    #connecting to the db
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    #inserting every row after the header into our db
    for row in reader:

        #convert delay into integer and handle missing values
        row[9] = int(row[9]) if row[9] else None
        row = [None if x == "" else x for x in row]

        #you have to run create_db.py before in order for that part to work
        sql = """ INSERT OR IGNORE INTO hist_train_delay 
                    ( station_id, 
                    start_station_name, 
                    end_station_name, 
                    train_name, 
                    train_type, 
                    departure_planned, 
                    departure_actual, 
                    arrival_planned, 
                    arrival_actual, 
                    delay_in_min ) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
                """
        counter_sql += 1

        if counter_sql % BATCH_SIZE == 0:
            conn.commit()
            print(f"Commited {counter_sql} rows")

        cur.execute(sql,row)

    conn.commit()

#Remark: there seems to be a mismatch between the huggingface dataset and our csv in terms of column names after row 3783000