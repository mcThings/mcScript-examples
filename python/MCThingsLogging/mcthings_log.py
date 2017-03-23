#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "1.3"
'''
Python 2.7
Quick Program to log mqtt data (normally from mcThings modules, but could work with anything)

Nick Waterton 13th January 2017: V 1.0: Initial Release
Nick Waterton 15th January 2017: V 1.2: Added Nan Handling. No warning on +/-5s publishing delays, fixed stupid mistakes.
Nick Waterton 15th January 2017: V 1.3: Added some primitive time zone handling. Added new command line options, and fixed some things...
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

def decode_payload(topic,payload):
    '''
    decode timestamp (if any), and format json for pretty printing
    '''
    global module_timezone
    indent = master_indent + 31 #number of spaces to indent json data
    timestamp = None
    
    module_id, tz_offset = module_tz_from_topic(topic)  #get module id and calculates tz offset if there is one
    
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
                    timestamp_value = float(timestamp_string)
                elif len(timestamp_string) <=10:
                    timestamp_value = int(timestamp_string)
                else:
                    timestamp_value = int(timestamp_string)/1000.0

                timestamp_value -= tz_offset    #compensate for tz offset
                timestamp = datetime.datetime.fromtimestamp(timestamp_value) #with local tz offset applied
                timestamp_str = str(timestamp)
                if tz_offset:
                    timestamp_str += " T%dhr" % int(tz_offset/3600) #show auto calculated tz offset

                current_time = datetime.datetime.now()  #with local tz applied
                publish_delay = (current_time - timestamp).total_seconds()
                if (timestamp  < current_time):
                    publish_delay *= -1
                    
                delay_hours = int(publish_delay/3600)
                
                if publish_delay > 45000 or publish_delay < -45000:    #date/time set wrong on module (more than 24 hours)
                    publish_delay_string = "Date/time not updated on module\n"
                    module_timezone.pop(module_id, None)
                elif publish_delay > 2000 or publish_delay < -2000 :    # (more than 1/2 hour) assume this is some sort of timezone shift
                    if arg.timezone:
                        publish_delay_string = "Detected Date/time timezone offset of %d hrs : correcting...\n" % (delay_hours)
                        if delay_hours < -12 or delay_hours > 12:
                            log.warn("tz conversion error: %s" % delay_hours)
                        else:
                            log.debug("Storing tz offset %d for module %s" %(delay_hours * 3600, module_id))
                            module_timezone[module_id] = delay_hours * 3600
                    else:
                        publish_delay_string = "Detected Date/time timezone offset of %d hrs\n" % (delay_hours)
                        
                elif publish_delay > 5 or publish_delay < -5:   #no warning on +/-5 seconds delay
                    publish_delay_string = "WARNING: Publishing Delay of : %.3f s\n" % -publish_delay
                else:
                    publish_delay_string = "Publishing Delay of          : %.3f s\n" % -publish_delay
            except ValueError as e:
                timestamp_str = e
        json_data_string = "\n".join((indent * " ") + i for i in (publish_delay_string+json.dumps(json_data, indent = 2)).splitlines())
        if timestamp:
            formatted_data = "Decoded timestamp: %s\n%s" % (timestamp_str, json_data_string)
        else:
            formatted_data = "Decoded JSON: \n%s" % (json_data_string)
            
    except ValueError as e:
        formatted_data = payload
    except Exception as e:
        log.warn("Error : %s" %e)
        formatted_data = payload

    return formatted_data
    
def module_tz_from_topic(topic):
    '''
    extracts the module id from the topic string.
    assumes the topic is of the format
    xxx/xxx/xxx/id/item but you can specify the location of the module id using the -m option
    also gets tz offset (in seconds) from global dict module_timezone (if there is one)
    returns 0 if there isn't
    returns "default" for module_id if it can't find one.
    returns: module_id, tz_offset
    '''
    global module_timezone
    if not module_timezone:
        module_timezone = {}
    
    tz_offset = 0
    module_id_offset = -1 - arg.module
    module_id = "default"
    
    try:    
        module_id = topic.split("/")[module_id_offset]

    except IndexError as e:
        log.error("%s getting module id from %s, position %d" %(e,topic,module_id_offset))
        arg.module = 1
        log.warn("changed position to 1 (next to last) - if this is not right, you may have to specify it yourself, using the -m option")
    
    try:
        if module_id in module_timezone.keys():
            tz_offset = module_timezone[module_id]
    
    except Exception as e:
        log.error("%s getting time zone for module id: %s from topic: %s" %(e,module_id,topic))
        
    return module_id, tz_offset
        
    
    
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
        log_string = decode_payload(msg.topic,msg.payload)
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
    parser.add_argument('-e','--echo', action='store_false', help='Echo to Console (default: True)', default = True)
    parser.add_argument('-D','--debug', action='store_true', help='debug mode', default = False)
    parser.add_argument('-r','--raw', action='store_true', help='Output raw data, no decoding of json data', default = False)
    parser.add_argument('-z','--timezone', action='store_false', help='Auto compensate for detected timezone offsets', default = True)
    parser.add_argument('-m','--module', action='store',type=int, default=1, help='Location in topic of module id (from the end of topic) example: 0 is end, 1 is next to last, default is 1')
    parser.add_argument('--version', action='version', version="%(prog)s ("+__version__+")")
    
    arg = parser.parse_args()
      
    #----------- Global Variables -----------
    broker_connected = False
    master_indent = arg.indent
    module_timezone = {}    #add module timezone offsets here - per module.
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
        if arg.timezone:
            log.info("Auto compensating for timestamp timezone offsets")
        else:
            log.info("Showing raw timestamps")
        
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
