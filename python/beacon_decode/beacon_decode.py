#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "1.21"
'''
Python 2.7
Quick Program to decode UDP and MQTT beacon data from mcThings modules
Can Decode both MQTT and UDP beacons, but really you only need one or the other
works for modules version 7-366
gateway version GW 7-361, LPLan 7-408

Nick Wateron 29th August 2016: V 1.0: Initial Release
Nick Waterton 1st Nov 2016: V 1.1: Added Lowbattery data type
Nick Waterton 24th Jauary 2017 V1.2: Added configuration for destination MQTT broker as different from source MQTT broker (for cloud configs etc)
Nick Waterton 24th Jauary 2017 V1.21: Added protocol selection
'''

#from __future__ import print_function  #if you want python 3 print function

#import mosquitto
import paho.mqtt.client as paho
import socket
import struct
import logging
import time
from logging.handlers import RotatingFileHandler

global sub_topic
sub_topic = "mcThings/beacon/+/"
global mqtt
global udp
global module
global data_decode
data_decode = { 0:"None",
                1:"Version",
                2:"Uptime",
                3:"BatteryVoltage",
                4:"Temperature",
                5:"Temperature2",
                6:"Humidity",
                7:"Dewpoint",
                8:"Pressure",
                9:"Altitude",
                10:"Motion",
                11:"Door",
                12:"Doorknock",
                13:"LowBattery"}    #add new types of data here

#----------- Start of Classes ------------
        
#----------- End of Classes ------------

#----------- Local Routines ------------

def decode_data(data, addr=None):
    '''
    Decode MQTT or UDP mcThings beacon data
    addr is for UDP only, is ip of gateway and port (ip,port)
    beacon format example (MQTT data misses first 3 bytes)
    EF:BF:BD:11:01:00:04:19:00:2B:EF:BF:BD:2E:13:01:00
                       X  X  X  X (user bytes - byte 1,3,2,4)
                                            X  X  X  X (Gateway id - reverse order = 01132E)
           X  X  X  X (Beacon ID reverse order 0111BD)
    order may be different!
    UDP beacon format example
    00:16:01:0D:BA:11:01:00:03:1B:00:06:C3:2E:13:01:00
    ProtocolVersion Byte 0x00 Version 0
    MessageType     Byte 0x16 Beacon Type (22)
    MessageVersion  Byte 0x01 Version 1
    MessageSize     Byte 0x0D Number of bytes to follow (13)
    DeviceUID       Uint32 Unique Identifier Device
    BeaconByte1     Byte User defined data
    BeaconByte2     Byte User defined data
    BeaconByte3     Byte User defined data
    BeaconByte4     Byte User defined data
    RSSI            Byte Relative Signal Strength Indicator
    GatewayUID      Uint32 Unique Identifier Gateway
    '''
    
    beacon_data = str(data)
    valid_data = True
    udp_data = False
    beacon_id = gateway_id = decode_bytes = ""
    value = None
    rssi = None
    protocolVersion = messageType = messageVersion = messageSize = data_type = 0
    topic_name = sub_topic.split("+")[0]
    
    #uncomment to decode all received bytes
    #decode_bytes = ":".join("{:02X}".format(ord(c)) for c in beacon_data)
    #log.debug("%s beacon decode: %s" % (topic_name decode_bytes))
    
    if addr is not None:    #UDP data
        protocolVersion,messageType,messageVersion,messageSize = struct.unpack("BBBB",beacon_data[0:4])
        beacon_data = beacon_data[4:]   #convert to same format as MQTT data
        if messageType == 0x16:
            udp_data = True
        else:                           #unsupported beacon type
            valid_data = False
      
    if valid_data:    
        beacon = beacon_data[0:4][::-1]  #reverse first 4 bytes string
        gateway = beacon_data[-4:][::-1] #reverse last 4 bytes string
        data = beacon_data[-9:-5]        #custom user data bytes
        rssi_part = beacon_data[-5:-4]   #rssi
        rssi = struct.unpack("b",rssi_part)[0]
        beacon_id = "".join("{:02X}".format(ord(c)) for c in beacon)
        gateway_id = "".join("{:02X}".format(ord(c)) for c in gateway)
        
        data_type, value = extract_data(data)  #decode your custom data here
        
        if value is not None:
            if udp_data:
                log.info("%s%s/%s UDP  decode: RSSI: %d" % (topic_name, gateway_id, beacon_id, rssi))
                log.info("%s%s/%s UDP  decode: %s: %0.3f" % (topic_name, gateway_id, beacon_id, data_decode[data_type], value))
            else:
                log.info("%s%s/%s MQTT decode: RSSI: %d" % (topic_name, gateway_id, beacon_id, rssi))
                log.info("%s%s/%s MQTT decode: %s: %0.3f" % (topic_name, gateway_id, beacon_id, data_decode[data_type], value))
        else:
            valid_data = False
            
    return protocolVersion,messageType,messageVersion,messageSize,gateway_id,beacon_id,rssi,data_type,value,valid_data
    
def extract_data(data):
    '''
    decode your own custom data here
    I use byte 1 as data type (see global dictionary data_decode{})
    byte 2,3 as integer part
    byte 4 as fractional part
    but you can decode however you want.
    '''
    value = None
    data_type = struct.unpack("B",data[0])[0]
    if data_type > 1:
        int_part = struct.unpack("<h", data[1:3])[0]
        fract_part = float(struct.unpack("b", data[3:])[0]) / 100.0
    elif data_type == 1: #deal with default "version number" broadcast by default
        int_part = struct.unpack("<B", data[1:2])[0]
        fract_part = float(struct.unpack("H", data[2:])[0]) / 1000.0
    else:
        return 0, None
    
    #log.debug("beacon decode: type %d int: %d fract: %0.2f" % (data_type, int_part, fract_part))
    if fract_part >= 1 or fract_part <= -1:
        decoded_data = ":".join("{:02X}".format(ord(c)) for c in data)
        log.error("Decode Error decode: %s = %s: int: %d fract: %0.3f" % (decoded_data, data_decode[data_type], int_part, fract_part))
    else:
        value = float(int_part) + fract_part

    return data_type, value
    
def publish_data(topic, beacon_id, data_type, value, rssi):
    try:
        mqttc.publish(topic+beacon_id+"/"+data_decode[data_type], value)
        mqttc.publish(topic+beacon_id+"/Rssi", rssi)
        if destbroker != None:
            mqttc_dest.publish(topic+beacon_id+"/"+data_decode[data_type], value)
            mqttc_dest.publish(topic+beacon_id+"/Rssi", rssi)
    except KeyError as e:
        pass
    
# Define event callbacks
def on_connect_dest(mosq, obj, rc):
    global broker_connected_dest
    broker_connected_dest = True
    log.info("connected to destination broker, rc: %s" % str(rc))
    
def on_disconnect_dest(mqttc, obj, rc):
    global broker_connected_dest
    if rc != 0:
        broker_connected_dest = False
        log.warn("Unexpected Disconnect From destination Broker - reconnecting")
    else:
        log.info("Disconnected From destination Broker")
        
    mqttc_dest.reconnect()

def on_connect(mosq, obj, rc):
    global broker_connected
    broker_connected = True
    log.info("connected to broker, rc: %s" % str(rc))
    if mqtt:
        log.info("subscribing to %s%s" % (sub_topic, module))
        mqttc.subscribe(sub_topic+module, 0)
    
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
    if msg.topic.startswith("mcThings/beacon"):
        protocolVersion,messageType,messageVersion,messageSize,gateway_id,beacon_id,rssi,data_type,value,valid_data = decode_data(msg.payload)
        if valid_data:
            publish_data(topic, beacon_id, data_type, value, rssi)
        
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
        formatter = logging.Formatter('[%(levelname)1.1s %(asctime)s] (%(threadName)-10s) %(message)s')
    else:
        formatter = logging.Formatter('%(message)s')
    fileHandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=2000000, backupCount=5)
    fileHandler.setFormatter(formatter)
    if console == True:
      streamHandler = logging.StreamHandler()

    l.setLevel(level)
    l.addHandler(fileHandler)
    if console == True:
      l.addHandler(streamHandler)   
    
if __name__ == '__main__':
    import argparse, sys
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(description='decode beacons for mcThings modules')
    parser.add_argument('-m','--mqtt', action='store_true', help='Only Decode MQTT beacons', default = False)
    parser.add_argument('-u','--udp', action='store_true', help='Only Decode UDP beacons', default = False)
    parser.add_argument('-i','--id', action='store',type=str, default="#", help='unique id of module to decode (default: All)')
    parser.add_argument('-t','--topic', action='store',type=str, default="MCThings/", help='topic to publish to (default: MCThings/)')
    parser.add_argument('-b','--broker', action='store',type=str, default="192.168.100.119", help='ipaddress of MQTT broker (default: 192.168.100.119)')
    parser.add_argument('-p','--port', action='store',type=int, default=1883, help='MQTT broker port number (default: 1883)')
    parser.add_argument('-U','--user', action='store',type=str, default=None, help='MQTT broker user name (default: None)')
    parser.add_argument('-P','--password', action='store',type=str, default=None, help='MQTT broker password (default: None)')
    parser.add_argument('--protocol', action='store_true', help='protocol 3.1.1 default, 3.1 if selected', default = False)
    parser.add_argument('--destbroker', action='store',type=str, default=None, help='ipaddress/hostname of destination MQTT broker (default: None)')
    parser.add_argument('--destport', action='store',type=int, default=1883, help='destination MQTT broker port number (default: 1883)')
    parser.add_argument('--destuser', action='store',type=str, default=None, help='destination MQTT broker user name (default: None)')
    parser.add_argument('--destpassword', action='store',type=str, default=None, help='destination MQTT broker password (default: None)')
    parser.add_argument('--destclientid', action='store',type=str, default="", help='destination MQTT broker client_id (default: "") if left blank, a random client id is assigned')
    parser.add_argument('-l','--log', action='store',type=str, default="/home/nick/Scripts/mcThings_beacon.log", help='path/name of log file (default: /home/nick/Scripts/mcThings_beacon.log)')
    parser.add_argument('-e','--echo', action='store_true', help='Echo to Console (default: True)', default = True)
    parser.add_argument('-D','--debug', action='store_true', help='debug mode', default = False)
    parser.add_argument('--version', action='version', version="%(prog)s ("+__version__+")")
    
    arg = parser.parse_args()
      
    #----------- Global Variables -----------
    broker_connected = False
    broker_connected_dest = False
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
    
    log.info("Decoding McThings modules beacon data")
    module = arg.id
    if module == "#":
        log.info("Decoding module: All")
    else:
        log.info("Decoding module: %s" % module)

    mqtt = arg.mqtt
    udp = arg.udp
    if mqtt == False and udp == False:    #if neither selected, decode both types of beacon
        mqtt = True
        udp = True
        
    if mqtt:
        log.info("Decoding MQTT beacons")
    if udp:
        log.info("Decoding UDP beacons")
    
    #broker = "127.0.0.1"  # mosquitto broker is running on localhost
    broker = arg.broker
    port = arg.port
    topic = arg.topic
    
    destbroker = arg.destbroker #only used for publishing...
    destport = arg.destport
    
    if arg.protocol:
        log.info("using old protocol 3.1")
        mqtt_protocol=paho.MQTTv31
    else:
        log.info("using protocol 3.1.1")
        mqtt_protocol=paho.MQTTv311

    mqttc = paho.Client(protocol=mqtt_protocol)
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
    
    #mqttc.will_set("MCThings/beacon", "Disconnected", 0, False)
    #mqttc.max_inflight_messages_set(200)    #set max inflight messages - default 20 (uses more memory)
    #mqttc.reconnect_delay_set(10, 30, True)
    
    try:
        if arg.user != None:
            mqttc.username_pw_set(arg.user, arg.password)
        mqttc.connect(broker, port, 60) # Ping MQTT broker every 60 seconds if no data is published from this script.       
    except socket.error:
        log.error("Unable to connect to MQTT Broker")
        
    try:        
        if destbroker != None:
            #different send broker to receive...
            log.info("Destination MQTT broker set to %s - connecting" % destbroker)
            mqttc_dest = paho.Client(client_id=arg.destclientid, protocol=mqtt_protocol)  #only used for publishing, so minnimal callbacks!
            mqttc_dest.on_connect = on_connect_dest
            mqttc_dest.on_disconnect = on_disconnect_dest
            if arg.destuser != None:
                mqttc_dest.username_pw_set(arg.destuser, arg.destpassword)
            mqttc_dest.connect(destbroker, destport, 60) # Ping MQTT broker every 60 seconds if no data is published from this script. 
    except socket.error:
        log.error("Unable to connect to destination MQTT Broker")
        
    try:
        print("<Cntl>C to Exit")
        
        if udp:
            #set up UDP socket to receive data from module
            port = 25452    #module beacon port
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("", port))  #bind all intefaces to port
            log.info("waiting on port: %d" % port)
        
        mqttc.loop_start()
        if destbroker != None:
            mqttc_dest.loop_start()
        #mqttc.loop_forever()
        #rc = 0
        #while rc == 0:
        while True:
            #rc = mqttc.loop()   #wait for mqtt data
            if udp:
                udp_data, addr = s.recvfrom(1024)   #wait for udp data
                if len(udp_data) > 0:
                    protocolVersion,messageType,messageVersion,messageSize,gateway_id,beacon_id,rssi,data_type,value,valid_data = decode_data(udp_data, addr)
                    if valid_data:
                        publish_data(topic, beacon_id, data_type, value, rssi)
            else:
                time.sleep(1)
        
    except KeyboardInterrupt:
        log.info ("Exit Program")  
        sys.exit()  
        
    finally:
        mqttc.loop_stop()
        mqttc.disconnect()
        if destbroker != None:
            mqttc_dest.loop_stop()
            mqttc_dest.disconnect()
        if udp:
            s.close()
        log.info ("Program Ended") 
