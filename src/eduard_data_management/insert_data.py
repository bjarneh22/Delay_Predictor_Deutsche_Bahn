from datetime import datetime, timezone

# define methods to add data to the tables
# description of workflow only for the first method (does not change for the other ones)
def add_station(conn, stations):

    # insert statement

    sql = ''' INSERT OR IGNORE INTO stations(station_id, location, latitude, longitude)
                  VALUES(?,?,?,?) '''

    cur = conn.cursor()

    # execute the insert statement
    cur.execute(sql, stations)

    # commit the changes
    conn.commit()

    # get the id of the last inserted row
    return cur.lastrowid

def add_journeys(conn, journeys):
    sql = ''' INSERT INTO journeys(train_line, start_station_id, 
                                    end_station_id, departure_time, planned_arrival_time, 
                                    actual_arrival_time, delay_minutes, collected_at)
                      VALUES(?,?,?,?,?,?,?,?) '''

    cur = conn.cursor()

    cur.execute(sql, journeys)

    conn.commit()

    return cur.lastrowid

def add_weather(conn, weather):
    sql = ''' INSERT OR REPLACE INTO weather(station_id, temperature, precipitation, wind_speed, collected_at)
                          VALUES(?,?,?,?,?)'''

    cur = conn.cursor()

    cur.execute(sql, weather)

    conn.commit()

    return cur.lastrowid