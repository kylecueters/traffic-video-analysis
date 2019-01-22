import sqlite3

conn = sqlite3.connect('dataCollected')
c = conn.cursor()

def create_table1_trafficRecordToSM():
    c.execute("CREATE TABLE IF NOT EXISTS trafficRecords_toSM(vehicleId TEXT, dateTimeStamp TEXT, distance REAL, speed REAL)")

def create_table1_trafficRecordToCalmar():
    c.execute("CREATE TABLE IF NOT EXISTS trafficRecords_toCalmar(vehicleId TEXT, dateTimeStamp TEXT, distance REAL, speed REAL)")

def create_table2_trafficDataToSM():
    c.execute("CREATE TABLE IF NOT EXISTS trafficData_toSM(dateTime TEXT, count REAL, avgSpeed REAL, flow REAL, density REAL)")

def create_table2_trafficDataToCalmar():
    c.execute("CREATE TABLE IF NOT EXISTS trafficData_toCalmar(dateTime TEXT, count REAL, avgSpeed REAL, flow REAL, density REAL)")


def data_entry1_toSM(w, x, y, z):
    vehicleId = w
    dateTimeStamp = x
    distance = y
    speed = z

    c.execute("INSERT INTO trafficRecords_toSM (vehicleId, dateTimeStamp, distance, speed) VALUES (?, ?, ?, ?)",
              (vehicleId, dateTimeStamp, distance, speed))
    conn.commit()

def data_entry1_toCalmar(w, x, y, z):

    vehicleId = w
    dateTimeStamp = x
    distance = y
    speed = z

    c.execute("INSERT INTO trafficRecords_toCalmar (vehicleId, dateTimeStamp, distance, speed) VALUES (?, ?, ?, ?)",
              (vehicleId, dateTimeStamp, distance, speed))
    conn.commit()

def data_entry2_toSM(v, w, x, y, z):
    dateTime = v
    count = w
    avgSpeed = x
    flow = y
    density = z

    c.execute("INSERT INTO trafficData_toSM(dateTime, count, avgSpeed, flow, density) VALUES (?, ?, ?, ?, ?)",
              (dateTime, count, avgSpeed, flow, density))
    conn.commit()

def data_entry2_toCalmar(v, w, x, y, z):
    dateTime = v
    count = w
    avgSpeed = x
    flow = y
    density = z

    c.execute("INSERT INTO trafficData_toCalmar(dateTime, count, avgSpeed, flow, density) VALUES (?, ?, ?, ?, ?)",
              (dateTime, count, avgSpeed, flow, density))
    conn.commit()

def closingDatabase():
    c.close()
    conn.close()
