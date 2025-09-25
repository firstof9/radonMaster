#!/usr/bin/env python

"""
Copyright(C) 2021, BrucesHobbies
All Rights Reserved

AUTHOR: BrucesHobbies
DATE: 3/01/2021
REVISION HISTORY
  DATE        AUTHOR          CHANGES
  yyyy/mm/dd  --------------- ------------------------------------------------
  2021/04/14  BrucesHobbies   Added support for Antonio's variable tone buzzer


OVERVIEW:
    Place holder for alert and publish-subscribe

LICENSE:
    This program code and documentation are for personal private use only. 
    No commercial use of this code is allowed without prior written consent.

    This program is free for you to inspect, study, and modify for your 
    personal private use. 

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.



--- if MQTT is used, basic commands for install of MQTT ---

sudo apt-get install mosquitto             # local broker
sudo apt-get install mosquitto-clients     # local publish-subscribe
sudo systemctl enable mosquitto            # Enable the broker and allow it to auto-start after reboot
sudo systemctl status mosquito             # Check status
hostname -I
ifconfig | grep inet | grep broadcast
sudo pip3 install paho-mqtt


--- if INFLUXDB is used, basic commands for install of INFLUXDB are found on web pages ---



--- Plan to add SQL ---


"""

import datetime
import json
import os
import sys
import time

from consts import (
    AIRTHINGS,
    AIRTHINGS_SENSORS,
    BUZZER,
    BUZZER_ENABLED,
    CSV_FILE,
    CSV_FILE_ENABLED,
    EMAIL_SMS,
    EMAIL_SMS_ENABLED,
    INFLUX_DB,
    INFLUX_DB_ENABLED,
    INFLUX_DBNAME,
    INFLUX_HOST,
    INFLUX_PASSWORD,
    INFLUX_PORT,
    INFLUX_USER,
    IP_PORT_ENABLED,
    MQTT,
    MQTT_ENABLED,
    MQTT_HOST,
    MQTT_KEEPALIVE_INTERVAL,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_SENSORS,
    MQTT_USERNAME,
    buzzerPIN,
)

mqtt_connected = False
mqtt_reconnect = False

#
# USER CONFIGURATION SECTION MOVED TO const.py

if MQTT_ENABLED:
    import paho.mqtt.client as mqtt

    mqttClient = mqtt.Client("RadonMaster", clean_session=False)

if EMAIL_SMS_ENABLED:
    import sendEmail

if INFLUX_DB_ENABLED:
    from influxdb import InfluxDBClient

if BUZZER_ENABLED:
    from threading import Timer

    import RPi.GPIO as GPIO


def connectPubScribe():
    global mqttClient
    global influxClient

    if MQTT_ENABLED:
        if MQTT_USERNAME and MQTT_PASSWORD:
            mqttClient.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqttClient.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
        mqttClient.on_disconnect = onDisconnect()
        mqttClient.on_connect = onConnect()
        mqttClient.loop_start()

    if EMAIL_SMS_ENABLED:
        sendEmail.loadJsonFile()
        # sendStatus("pubScribe.py", " Program start")

    if INFLUX_DB_ENABLED:
        influxClient = InfluxDBClient(
            INFLUX_HOST, INFLUX_PORT, INFLUX_USER, INFLUX_PASSWORD, INFLUX_DBNAME
        )

    if BUZZER_ENABLED:
        # GPIO.setwarnings(False)           # Remove warning message
        GPIO.setmode(GPIO.BCM)  # Set the pin mode to BOARD mode
        GPIO.setup(buzzerPIN, GPIO.OUT)  # Buzzer is output mode

    return


def disconnectPubScribe():
    if MQTT_ENABLED:
        mqtt_reconnect = False
        topic = "RadonMaster/Status"
        pubRecord(MQTT, topic, "offline")
        mqttClient.disconnect()

    if BUZZER_ENABLED:
        GPIO.cleanup()

    return


def onConnect():
    """Handle mqtt connections."""
    print("MQTT connected!")
    # Set bools to control reconnections
    mqtt_connected = True
    mqtt_reconnect = True


def onDisconnect():
    """Attempt to reconnect on disconnection."""
    mqtt_connected = False
    print("MQTT disconnected attempting to reconnect...")
    while not mqtt_connected and mqtt_reconnect:
        try:
            mqttClient.reconnect()
            print("MQTT reconnected!")
        except Exception as error:
            print("Exception [%s]: %s", type(error).__name__, error)


def attachFunction():
    return


def ha_discovery(serial: str = "00000000"):
    """Generate Home Assistant discovery topics."""
    mqtt_data = {}
    mqtt_data["availability_topic"] = "RadonMaster/Status"
    mqtt_data["device"] = {
        "identifiers": ["radonmaster"],
        "manufacturer": "Radon Master",
        "name": "Radon Master",
        "model": "Radon Master",
    }
    mqtt_data["origin"] = {"name": "Radon Master"}

    for sensor in MQTT_SENSORS:
        topic = f"homeassistant/sensor/RadonMaster/{sensor}/config"
        mqtt_data["unique_id"] = f"radonmaster-{serial}-{sensor}"
        mqtt_data["default_entity_id"] = f"radonmaster_{sensor}"
        mqtt_data["name"] = MQTT_SENSORS[sensor]["name"]
        mqtt_data["device_class"] = MQTT_SENSORS[sensor]["device_class"]
        mqtt_data["unit_of_measurement"] = MQTT_SENSORS[sensor]["unit_of_measurement"]
        mqtt_data["value_template"] = MQTT_SENSORS[sensor]["value_template"]
        mqtt_data["state_topic"] = MQTT_SENSORS[sensor]["state_topic"]
        mqtt_data["suggested_display_precision"] = MQTT_SENSORS[sensor][
            "suggested_display_precision"
        ]

        try:
            mqttClient.publish(topic, json.dumps(mqtt_data), 1, True)
        except Exception as error:
            print("Exception [%s]: %s", type(error).__name__, error)

    if AIRTHINGS:
        for sensor in AIRTHINGS_SENSORS:
            topic = f"homeassistant/sensor/RadonMaster/{sensor}/config"
            mqtt_data["unique_id"] = f"radonmaster-{serial}-{sensor}"
            mqtt_data["default_entity_id"] = f"radonmaster_{sensor}"
            mqtt_data["name"] = AIRTHINGS_SENSORS[sensor]["name"]
            mqtt_data["device_class"] = AIRTHINGS_SENSORS[sensor]["device_class"]
            mqtt_data["unit_of_measurement"] = AIRTHINGS_SENSORS[sensor][
                "unit_of_measurement"
            ]
            mqtt_data["value_template"] = AIRTHINGS_SENSORS[sensor]["value_template"]
            mqtt_data["state_topic"] = AIRTHINGS_SENSORS[sensor]["state_topic"]
            mqtt_data["suggested_display_precision"] = AIRTHINGS_SENSORS[sensor][
                "suggested_display_precision"
            ]

            try:
                mqttClient.publish(topic, json.dumps(mqtt_data), 1, True)
            except Exception as error:
                print("Exception [%s]: %s", type(error).__name__, error)


#
# Publish data record
# dest: [MQTT, CSV_FILE, EMAIL_SMS, INFLUX_DB]
# topic: 'topic/subtopic', 'topic/subtopic/alert', or etc.
# data: dict, list, or str
#
def pubRecord(dest, topic, data, hdr=""):
    # print("DEST: ", dest, " TOPIC: ", topic, " DATA: ", data, " HDR: ", hdr)

    if MQTT_ENABLED and (MQTT in dest):
        if not isinstance(data, str):
            msg = json.dumps(data)
        else:
            msg = data
        mqttClient.publish(topic, msg, 1, True)

    if CSV_FILE_ENABLED and (CSV_FILE in dest):
        writeCsv(topic, data, hdr)

    if EMAIL_SMS_ENABLED and (EMAIL_SMS in dest):
        if not isinstance(data, str):
            msg = str(data)
        # if not isinstance(data,str) :
        #     msg = json.dumps(data, indent=4)
        else:
            msg = data

        upperTopic = topic.upper()
        if "ALERT" in upperTopic:
            sendAlert(topic, msg)
        elif "STATUS" in upperTopic:
            sendStatus(topic, msg)

    if INFLUX_DB_ENABLED and (INFLUX_DB in dest):
        if not isinstance(data, str):
            msg = json.dumps(data)
        else:
            msg = data
        influxClient.write_points(msg)

    if BUZZER_ENABLED and (BUZZER in dest):
        buzzerOn(data)

    return


#
# CSV files
#
topicFmtStr = {}  # format string for data records in a topic's csv file
topicFiles = {}  # Dictionary of csv files that exist

#
# Enables custom format strings per topic when writting csv files
#
def addTopicFmtStr(topic, fmtStr):
    topicFmtStr[topic] = fmtStr


#
# For new files, create a header row using dict or from hdr
#
def addTopicFileHeaders(filename, topic, data, hdr=""):
    result = ""

    if not (topic in topicFiles):
        topicFiles[topic] = hdr
        if not os.path.isfile(filename):
            # If csv log file does not exist, write header
            result = "UNIX time (s),DateTime,"

            if isinstance(data, dict):
                # print("dict: ", data)
                result += ",".join("{}".format(k) for k in data)  # keys
                # print(result)

            else:
                # print("Else: ", hdr)
                result += hdr
                # print(result)

            result += "\n"

    return result


#
# Append data to CSV file
#
def writeCsv(topic, data, hdr=""):
    filename = topic.replace("/", "_") + ".csv"
    # print("Filename: ", filename)

    s = addTopicFileHeaders(filename, topic, data, hdr)

    s += (
        str(round(time.time()))
        + ","
        + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,")
    )

    if isinstance(data, dict):
        s += ",".join("{}".format(v) for k, v in data.items())  # values

    elif isinstance(data, list):
        if topic in topicFmtStr:
            s += topicFmtStr[topic].format(*data)
        else:
            s += ("{}," * len(data)).format(*data)

    elif isinstance(data, str):
        s += data

    else:
        print("Type not supported")

    # write interval data to csv file
    with open(filename, "a") as csvFile:
        csvFile.write(s + "\n")
        csvFile.close()


#
# EMAIL SMS
#

#
# Send alert via email to another email or as SMS text
#
def sendAlert(subj, msg):
    msg = time.strftime("%a, %d %b %Y %H:%M:%S \n", time.localtime()) + msg
    sendEmail.send_mail(sendEmail.ALERT_USERID, subj, msg)


#
# Send status via email to another email or as SMS text
#
def sendStatus(subj, msg):
    msg = time.strftime("%a, %d %b %Y %H:%M:%S \n", time.localtime()) + msg
    sendEmail.send_mail(sendEmail.STATUS_USERID, subj, msg)


#
# Buzzer On
#
buzzer = []


def buzzerOn(data):
    global buzzer
    print(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S "),
        "Buzzer On",
        " F: ",
        data.get("Frequency", 700),
        " DC: ",
        data.get("Dutycycle", 10),
        " Duration(s): ",
        data.get("Duration", 10),
    )

    buzzer = GPIO.PWM(buzzerPIN, data.get("Frequency", 700))  # Default is 700 Hz
    buzzer.start(data.get("Dutycycle", 10))  # Default is 10%
    Timer(data.get("Duration", 10), buzzerOff).start()  # Default is 10 seconds


#
# Buzzer Off
#
def buzzerOff():
    global buzzer
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S "), "Buzzer Off")
    buzzer.stop()


#
# Test / debug
#
if __name__ == "__main__":

    print("\nPress CTRL+C to exit...\n")

    connectPubScribe()

    topic = "Sensor"
    dictVar = {"Current": 6.4, "Power": 3.2, "Energy": 4.5, "PF": 0.95}
    pubRecord(CSV_FILE, topic, dictVar)

    topic = "Sensor/Alert"
    listVar = [6.4, 3.2, 4.5, 0.95]
    pubRecord(CSV_FILE, topic, listVar, "Col1,Col2,Col3,Col4")

    fmtStr = "{:.1f},{:.2f},{:.3f},{:.4f}"
    addTopicFmtStr(topic, fmtStr)
    pubRecord(CSV_FILE, topic, listVar, "Col1,Col2,Col3,Col4")

    topic = "Sensor/topic"
    sVar = "6.4, 3.2, 4.5, 0.95"
    pubRecord(CSV_FILE, topic, sVar, "Col1,Col2,Col3,Col4")

    # Test buzzer
    if BUZZER_ENABLED:
        pubRecord(BUZZER, "", {"Frequency": 500, "Dutycycle": 20, "Duration": 20})
        time.sleep(60)

        pubRecord(BUZZER, "", {})
        time.sleep(60)

        pubRecord(BUZZER, "", {"Frequency": 900, "Dutycycle": 30, "Duration": 40})
        time.sleep(60)

    disconnectPubScribe()

