#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "1.1"
'''
Python 2.7
Quick Program to log mqtt data (normally from mcThings modules, but could work with anything)

Nick Waterton 13th January 2017: V 1.0: Initial Release
Nick Waterton 15th January 2017: V 1.1: Added Nan Handling. No warning on +/-5s publising delays
'''

#from __future__ import print_function  #if you want python 3 print function

#import mosquitto
import paho.mqtt.client as paho
import json
import datetime
from collections import OrderedDict
import logging
import time
from logging.handlers import RotatingFileHandler

#----------- Start of Classes ------------
        
#----------- End of Classes ------------

#----------- Local Routines ------------

def decode_payload(payload):
    '''
    decode timestamp (if any), and format json for pretty printing
    '''
    indent = master_indent + 31 #number of spaces to indent json data
    try:
        #if it's json data, decode it (use OrderedDict to preserve keys order), else return as is...
        json_data = json.loads(payload.replace(":nan", ":NaN"), object_pairs_hook=OrderedDict)
        if not isinstance(json_data, dict): #if it's not a dictionary, probably just a number
            return json_data
        publish_delay_string = ''
        if "time" in json_data.keys():
            try:
                timestamp_string = str(json_data['time'])

                if "." in timestamp_string:
                    timestamp = datetime.datetime.fromtimestamp(float(timestamp_string))
                elif len(timestamp_string) <=10:
                    timestamp = datetime.datetime.fromtimestamp(int(timestamp_string))
                else:
                    timestamp = datetime.datetime.fromtimestamp(int(timestamp_string)/1000.0)
                current_time = datetime.datetime.now()
                publish_delay = (current_time - timestamp).total_seconds()
                
                if publish_delay > 5000:    #date/time set wrong on module
                    publish_delay_string = "Date/time not updated on module\n"
                elif publish_delay > 5 or publish_delay < -5:   #no warning on +/-5 seconds delay
                    publish_delay_string = "WARNING: Publishing Delay of : %.3f s\n" % publish_delay
                else:
                    publish_delay_string = "Publishing Delay of          : %.3f s\n" % publish_delay
            except ValueError as e:
                timestamp = e
        json_data_string = "\n".join((indent * " ") + i for i in (publish_delay_string+json.dumps(json_data, indent = 2)).splitlines())
        formatted_data = "Decoded timestamp: %s\n%s" % (timestamp, json_data_string)
    #except ValueError as e:
    except Exception as e:
        log.warn("Error Decoding json: %s" %e)
        formatted_data = payload

    return formatted_data
    
# Define event callbacks
def on_connect(mosq, obj, rc):
    global broker_connected
    broker_connected = True
    log.debug("connected to broker, rc: %s" % str(rc))
    log.info("subscribing to %s" % (sub_topic))
    mqttc.subscribe(sub_topic, 0)
    
def on_disconnect(mqttc, obj, rc):
    global broker_connected
    if rc != 0:
        broker_connected = False
        log.warn("Unexpected Disconnect From Broker - reconnecting")
    else:
        log.info("Disconnected From Broker")
        
    mqttc.reconnect()

def on_message(mosq, obj, msg):
    #log.debug("%s, %s, %s" % (msg.topic, str(msg.qos), str(msg.payload)))
    global master_indent
    if arg.indent == 0:
        master_indent = max(master_indent, len(msg.topic))
    if arg.raw:
        log_string = msg.payload
    else:
        log_string = decode_payload(msg.payload)
    log.info("%-{:d}s : %s".format(master_indent) % (msg.topic,log_string))
        
def on_publish(mosq, obj, mid):
    #log.debug("mid: " + str(mid))
    pass

def on_subscribe(mosq, obj, mid, granted_qos):
    log.debug("Subscribed: %s %s" % (str(mid), str(granted_qos)))

def on_log(mosq, obj, level, string):
    log.debug(string)
        
def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
    l = logging.getLogger(logger_name)
    if logger_name == 'Main':
        formatter = logging.Formatter('[%(levelname)1.1s %(asctime)s] %(message)s')
    else:
        formatter = logging.Formatter('%(message)s')
    fileHandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=2000000, backupCount=5)
    fileHandler.setFormatter(formatter)
    if console == True:
      streamHandler = logging.StreamHandler()

    l.setLevel(level)
    l.addHandler(fileHandler)
    if console == True:
      streamHandler.setFormatter(formatter)
      l.addHandler(streamHandler)   
    
if __name__ == '__main__':
    import argparse, sys
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(description='Log MQTT data for mcThings modules')
    parser.add_argument('-t','--topic', action='store',type=str, default="MCThings/#", help='MQTT Topic to subscribe to (can use wildcards # and +)')
    parser.add_argument('-b','--broker', action='store',type=str, default="192.168.100.119", help='ipaddress of MQTT broker (default: 192.168.100.119)')
    parser.add_argument('-p','--port', action='store',type=int, default=1883, help='MQTT broker port number (default: 1883)')
    parser.add_argument('-U','--user', action='store',type=str, default=None, help='MQTT broker user name (default: None)')
    parser.add_argument('-P','--password', action='store',type=str, default=None, help='MQTT broker password (default: None)')
    parser.add_argument('-i','--indent', action='store',type=int, default=0, help='Default indentation=auto')
    parser.add_argument('-l','--log', action='store',type=str, default="/home/nick/Scripts/mcThings.log", help='path/name of log file (default: /home/nick/Scripts/mcThings.log)')
    parser.add_argument('-e','--echo', action='store_true', help='Echo to Console (default: True)', default = True)
    parser.add_argument('-D','--debug', action='store_true', help='debug mode', default = False)
    parser.add_argument('-r','--raw', action='store_true', help='Output raw data, no decoding of json data', default = False)
    parser.add_argument('--version', action='version', version="%(prog)s ("+__version__+")")
    
    arg = parser.parse_args()
      
    #----------- Global Variables -----------
    broker_connected = False
    master_indent = arg.indent
    #-------------- Main --------------
     
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
            
    #setup logging
    setup_logger('Main', arg.log,level=log_level,console=arg.echo)

    log = logging.getLogger('Main')
    
    #------------ Main ------------------

    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")
    
    log.debug("-- DEBUG Mode ON -")
    
    log.info("Logging McThings modules MQTT data")
    if arg.raw:
        log.info("Showing RAW data")
    else:
        log.info("Showing DECODED data")
        
    if arg.indent == 0:
        log.info("Using auto indenting")
    
    #broker = "127.0.0.1"  # mosquitto broker is running on localhost
    broker = arg.broker
    port = arg.port
    sub_topic = arg.topic

    mqttc = paho.Client()
    # Assign event callbacks
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe

    if arg.debug:
        # Uncomment To enable debug messages
        #mqttc.on_log = on_log
        pass
    
    #mqttc.reconnect_delay_set(10, 30, True)
    try:
        if arg.user != None:
            mqttc.username_pw_set(arg.user, arg.password)
        mqttc.connect(broker, port, 60) # Ping MQTT broker every 60 seconds if no data is published from this script.       
    except socket.error:
        log.error("Unable to connect to MQTT Broker")
        
    try:
        print("<Cntl>C twice to Exit")

        mqttc.loop_forever()
        
    except (KeyboardInterrupt, SystemExit):
        log.info ("Exit Program")  
        sys.exit()  
        
    finally:
        mqttc.loop_stop()
        mqttc.disconnect()
        log.info ("Program Ended") 
