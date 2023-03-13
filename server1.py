import random
import time
from paho.mqtt import client as mqtt_client
import psycopg2
import threading
from datetime import datetime

# Python script which functions as a mqtt_client.
# It will listen for messages and then input them into a database.
# At the same time it will alter that data and send that data
# into a new database.

# variables used for mqtt connection
broker = '158.38.67.229'
port = 1883
topic = "RTUIot/Ard1/BMP280/Temp"
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'ntnu'
password = 'ntnuais2103'
msgDc = 'no message recieved'
running = True
date = datetime.now()
dateReformated = ''
processedDB = None
proCur = None

# Establishes a connection to a MQTT broker
# Returns the client (communication channel)
def connect_mqtt(broker, port, client_id):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

# Function which will end the loop and finish
def stop():
    global running
    input('Press ENTER to stop\n')
    running=False

# Subscribes to a topic the MQTT broadcaster communicates
# Only accepts a mqtt_client class
def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        global msgDc
        msgDc = msg.payload.decode()
        date = datetime.now()
        dateReformated = date.strftime('%Y-%m-%d %H:%M:%S')
        print(dateReformated + ' Message recieved: ' + msgDc)

    client.subscribe(topic)
    client.on_message = on_message

# Publishes a message on that topic
def publish(client: mqtt_client,topic, msg):
    client.publish(topic, msg)

# Adds a '0' padding to a single digit number
def getDoubleDigit(num):
    doubleDigitString = str(num)
    if(num < 10):
        doubleDigitString = '0' + str(num)
    return doubleDigitString

# Quereys data from the database and gets the average temperature
# of the last minute, and then sends that information to a new
# database.
lastDate = datetime.now()
def averageTempLastMinute(cursor):
    global dateReformated
    global lastDate
    global proCur
    curTime = datetime.now()
    # If statement which checks if a minute has passed (this minute is based on the internal clock not since the program started)
    if(lastDate.minute != curTime.minute):
        # Quereys last minutes data from the database
        cursor.execute('SELECT * FROM raw_data WHERE received_date BETWEEN %s AND %s', (dateReformated[:14] + getDoubleDigit(curTime.minute-2) + ':59', dateReformated[:14] + getDoubleDigit(curTime.minute) + ':00'))
        rows = cursor.fetchall()
        totalNum = 0
        for row in rows:
            totalNum += row[1]
        averageTemp = round(totalNum / len(rows), 2) # Gets the average temperature
        print('Average temprature last minute: ' + str(averageTemp))
        proCur.execute('INSERT INTO processed_data(received_date, processed_data) VALUES(%s,%s)', (curTime.strftime('%Y-%m-%d %H:%M'), averageTemp)) # Inserts average temprature into other database
    lastDate = datetime.now()


def run():

    global processedDB
    global proCur

    threading.Thread(target=stop).start()

    #threading.Thread(target=averageTempLastMinute).start()

    publisherClient = connect_mqtt('158.38.67.229', 1883, '1')
    subscriberClient = connect_mqtt('158.38.67.229', 1883, '2')
    subscribe(subscriberClient)

    rawDB = psycopg2.connect(
        host='localhost',
        database='raw_data',
        user='postgres',
        password='admin'
        port='5432'
    )
    rawDB.autocommit = True
    cur = rawDB.cursor()

    processedDB = psycopg2.connect(
        host='localhost',
        database='processed_data',
        user='postgres',
        password='admin'
        )
    processedDB.autocommit = True

    proCur = processedDB.cursor()

    while(subscriberClient.is_connected and running):
        subscriberClient.loop()
        global date
        date = datetime.now()
        global dateReformated
        dateReformated = date.strftime('%Y-%m-%d %H:%M:%S')
        if(msgDc != 'no message recieved'):
            cur.execute('INSERT INTO raw_data(received_date, raw_data) VALUES(%s,%s)', (dateReformated, msgDc))
            averageTempLastMinute(cur)
            #publish(publisherClient, "Test", msgDc)
    cur.close()
    rawDB.close()
    proCur.close()
    processedDB.close()
    subscriberClient.disconnect()
    publisherClient.disconnect()
    print('successfully disconnected')


if __name__ == '__main__':
    run()