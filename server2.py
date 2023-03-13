from flask import Flask
from flask import render_template
import psycopg2
from datetime import datetime
import json
import threading
import server1

app = Flask(__name__)

rawDB = psycopg2.connect(
        host='localhost',
        database='processed_data',
        user='postgres',
        password='admin'
        )

cur = rawDB.cursor()

# Adds '0' padding to a single digit number
def getDoubleDigit(num):
    doubleDigitString = str(num)
    if(num < 10):
        doubleDigitString = '0' + str(num)
    return doubleDigitString

# Gets data for the last hour from the database
def getLastHourDataFromDB():
    xDATA = []
    yDATA = []
    global cur
    time = datetime.now()
    timeFormated = time.strftime('%Y-%m-%d %H:%M:%S')
    hourInt = time.hour
    dayInt = time.day
    if(time.hour == 0):
        hourInt = 24
        dayInt = time.day-1
    cur.execute('SELECT * FROM processed_data WHERE received_date > %s', (timeFormated[:8] + getDoubleDigit(dayInt) + ' ' + getDoubleDigit(hourInt-1) + timeFormated[13:],))
    rows = cur.fetchall()
    for row in rows:
        print(row)
        xDATA.append(row[0].strftime('%Y-%m-%d %H:%M'))
        yDATA.append(row[1])
    return xDATA, yDATA

# Home page
@app.route('/')
def index():
    xDATA, yDATA = getLastHourDataFromDB()
    return render_template('index.html', xGraphData = xDATA, yGraphData = yDATA)

# Runs the MQTT client at the same time as the flask web server
def mqttClient():
    server1.run()

threading.Thread(target=mqttClient).start()

app.run(host='0.0.0.0', port=3000)