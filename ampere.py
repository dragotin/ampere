#!/usr/bin/python3

# Klaas Freitag <kfreitag@owncloud.com>
# distribute under GPLv2 or ask
#
# Read current from a tasmota device (power plug) and push it on to a self
# modified mechanical Ampere Meter -  Kudos Jürgen W.

import threading
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
import serial, sys, time
import os, stat, sys
import configparser

from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# configuration - edit here: 

config = configparser.ConfigParser()

config['ocis'] = { 
  'tasmoUrl': 'http://192.168.0.100',
  'maxMilliAmp': 250,
  'bucket': 'energytest',
  'sysmonUrl' : 'http://ocishc4:5000' }

config['NC'] = { 
  'tasmoUrl': 'http://192.168.0.103', # The URL of the tasmota device.
  'maxMilliAmp': 250,
  'bucket': 'energytest',
  'sysmonUrl' : 'http://phphc4:5000' }

# Settings to output measurements into a named pipe.
# Set the pipe variable to a path to let the script write
# results to the named pipe with that name.
_pipe = None # '/tmp/ampere.pipe'

# Influx configuration
# Set _influxUrl to None for no influx output
_influxUrl = "http://localhost:8086"

# generate a Token from the "Tokens Tab" in the UI
#
_token = "i5nFUqvsmJ3aPpJx0TbpGH8l1s4eRnGiDNd59daF3QNACwhg7IFQSWWGpraonJSEqjVMWZwIQ0EMlfP9PSVOgQ=="
# Organisation and bucket name for Influx
_org = "ownCloud"

### ======== don't touch below here

# The net plug device is supposed to provide this API:
# [kf:~] $ http 'http://192.168.0.102/cm?cmnd=Status%2010'
# HTTP/1.1 200 OK
# Accept-Ranges: none
# Cache-Control: no-cache, no-store, must-revalidate
# Connection: close
# Content-Type: application/json
# Expires: -1
# Pragma: no-cache
# Server: Tasmota/12.1.1 (ESP8285)
# Transfer-Encoding: chunked

# {
#     "StatusSNS": {
#        "ENERGY": {
#            "ApparentPower": 55,
#            "Current": 0.231,
#            "Factor": 0.64,
#            "Power": 35,
#            "ReactivePower": 42,
#            "Today": 0.029,
#            "Total": 0.226,
#            "TotalStartTime": "2022-09-24T13:23:21",
#            "Voltage": 237,
#            "Yesterday": 0.197
#        },
#        "Time": "2022-09-25T20:19:28"
#    }
# }
#



def slurp(ser):
  # slurp whatever is incoming.
  while ser.in_waiting > 0:
    print(ser.read(1))

def moveto(x):
  # time.sleep(0.1)
  slurp(ser)
  ser.write(b"P %d\n" % x)
  # time.sleep(0.1)

def led(r, g, b, first=None, last=None):
  if not ser:
    return

  if last is None: last = first
  time.sleep(0.1)
  if first is None:
    ser.write(b"C %d %d %d\n" % (r,g,b))
  else:
    ser.write(b"C %d %d %d %d %d\n" % (r,g,b,first,last))
  time.sleep(0.1)

def color(percent):
  # 100% means r = 255
  # 50%  means r = 255, g = 255
  # 0%   means g = 255
  r = 2.5 * percent 
  g = 255 - (2.5 * percent)
  b = 0
  led(r, g, b, 8, 25)

def toAmperemeter(milliAmp):
  # The firmware moves the zeiger from 0..100
  maxMilli = int(config[_service]['maxMilliAmp'])
  if milliAmp > maxMilli:
    milliAmp = maxMilli-1

  divisor = float(100.0/maxMilli)

  mover = int(milliAmp * divisor)
  print( "XX Normalized value (0..100): {0}".format(mover))
  moveto( mover)
  color(mover)
  _prevCurrent = milliAmp


# Not yet used or working - feed data to InfluxDB
def toInflux(service, timestamp, current):

  if _influxUrl == None:
    return

  with InfluxDBClient(url=_influxUrl, token=_token, org=_org) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    data = "current,system=%s current=%s" % (service, current)
    write_api.write(config[service]['bucket'], _org, data)
    client.close()

def toNamedPipe(timestamp, current):
  if _pipe == None:
    return

  t = timestamp # .replace("T", " ")
  p = "{timestamp};{current}.0\r\n".format(timestamp=t, current = current)

  fifo = open(_pipe, "a")
  fifo.write(p)
  fifo.close

def handleCurrentCurrent(service, timestamp, current, prevValue):
  if ser != None  and current != prevValue:
    toAmperemeter(current) # todo: Amperemeter per service

  toInflux(service, timestamp, current)

  if _pipe != None and stat.S_ISFIFO(os.stat(_pipe).st_mode):
    toNamedPipe(timestamp, current)

def fetchCurrent(service, prevValue):
  # print ("Fetching Current!")
  url = config[service]['tasmoUrl']

  current = prevValue # in case there is an exception or error, we need a proper value for the next call.

  try:
    r = requests.get( url+'/cm?cmnd=Status%2010', verify=False, timeout=4)
    
    if r.status_code == 200:
      # awesome result
      data = r.json()

      currentF = float(data["StatusSNS"]["ENERGY"]["Current"])
      current = int(currentF * 1000)
      timestamp = data["StatusSNS"]["Time"]

      print( "Measurement on {0}: {1} {2} mA".format(service, timestamp, current) )

      handleCurrentCurrent(service, timestamp, current, prevValue)
    else:
      print( "Request not successful with resultcode != 200")
  except ConnectTimeout:
    print('Request has timed out')
  except ReadTimeout:
    print('Request has timed out to read')

  # call this every three seconds, with the current val as prev value
  threading.Timer(3.0, fetchCurrent, [service, current]).start()

def fetchSysMon(service):
  if _influxUrl == None:
    return

  url = config[service]['sysmonUrl'] + '/getsys'
  print("Sysmon URL: %s"% url)
  try:
    r = requests.get(url, verify=False, timeout=4)

    if r.status_code == 200:
      # awesome result
      data = r.json()

      with InfluxDBClient(url=_influxUrl, token=_token, org=_org) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        datastr = "sysmon,system=%s cpu=%s,mem=%s,netin=%s,netout=%s" % (service, data["cpu_p"], data["mem_p"], data["nin"], data["nout"])
        print( "datastring: %s"% datastr)
        write_api.write("sysmon", _org, datastr)
        client.close()
  except ConnectTimeout:
    print('Request has timed out to connect')
  except ReadTimeout:
    print('Request has timed out to read')


  threading.Timer(3.0, fetchSysMon, [service]).start()

# =====================================================================
# main starts here
#
ser = None

if len(sys.argv) < 2:
  print("\nNo Amperemeter port given as command line option.\n\nAvailable ports are:")

  import serial.tools.list_ports as L

  for p in map(lambda x: x.device, L.comports()):
     print("  " + p)
  print("\n")

else:
  ser = serial.Serial(sys.argv[1], baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)
  _amperemeter = True

# Initialize the named pipe that can be read by tools like LabPlot

if _pipe != None:
  try:
    os.mkfifo(_pipe)
  except OSError as e:
    print ("Failed to create FIFO: %s" % e)

  print ("Named pipe receives data: %s" % _pipe)

# Start the timer here, with 0 as previous value:
# threading.Timer(3.0, fetchCurrent, [0]).start()
print ("Measurement starts in a few seconds")

# start the system monitor
# threading.Timer(3.0, fetchSysMon, ['ocis']).start()
# time.sleep(1)
# threading.Timer(3.0, fetchSysMon, ['NC']).start()

# start the energy measuring per service
threading.Timer(3.0, fetchCurrent, ['ocis', 0]).start()
time.sleep(1)
threading.Timer(3.0, fetchCurrent, ['NC', 0]).start()

# Some nice lights in the ammeter device:
led(0,0,0,   0,  82)


