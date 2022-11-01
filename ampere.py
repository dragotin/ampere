#!/usr/bin/python3

# Klaas Freitag <kfreitag@owncloud.com>
# distribute under GPLv2 or ask
#
# Read current from a tasmota device (power plug) and push it on to a self
# modified mechanical Ampere Meter -  Kudos Jürgen W.

import threading
import requests
import serial, sys, time
import os, stat, sys

from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# configuration - edit here: 

# The URL of the tasmota device.
_tasmoUrl = 'http://192.168.0.100'

# maximum current in milli ampere
_maxMilliAmp = 250

# Settings to output measurements into a named pipe.
# Set the pipe variable to a path to let the script write
# results to the named pipe with that name.
_pipe = None # '/tmp/ampere.pipe'

# Influx configuration
# Set _influxUrl to None for no influx output
_influxUrl = "http://localhost:8086"

# generate a Token from the "Tokens Tab" in the UI
#
_token = "hrKLJ9wfkN-cKLpGhl7Zd2uMs-vkSeQbEfsdo3YRkhtoh94gwwjav_z8tPbiUu7qr4x0eYN21IKSSa5-qqCqSA=="

# Organisation and bucket name for Influx
_org = "ownCloud"
_bucket = "ocis1"

# The system monitoring: Specify the URL to fetch the system params
_sysmonUrl = 'http://192.168.0.106:5000'

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
  if milliAmp > _maxMilliAmp:
    milliAmp = _maxMilliAmp-1

  divisor = float(100.0/_maxMilliAmp)

  mover = int(milliAmp * divisor)
  print( "XX Normalized value (0..100): {0}".format(mover))
  moveto( mover)
  color(mover)
  _prevCurrent = milliAmp


# Not yet used or working - feed data to InfluxDB
def toInflux(timestamp, current):

  if _influxUrl == None:
    return

  with InfluxDBClient(url=_influxUrl, token=_token, org=_org) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    data = "current,system=oCIS current=%s" % current
    write_api.write(_bucket, _org, data)
    client.close()

def toNamedPipe(timestamp, current):
  if _pipe == None:
    return

  t = timestamp # .replace("T", " ")
  p = "{timestamp};{current}.0\r\n".format(timestamp=t, current = current)

  fifo = open(_pipe, "a")
  fifo.write(p)
  fifo.close

def handleCurrentCurrent(timestamp, current, prevValue):
  if ser != None  and current != prevValue:
    toAmperemeter(current)

  toInflux(timestamp, current)

  if _pipe != None and stat.S_ISFIFO(os.stat(_pipe).st_mode):
    toNamedPipe(timestamp, current)

def fetchCurrent(prevValue):
  # print ("Fetching Current!")
  
  r = requests.get(_tasmoUrl + '/cm?cmnd=Status%2010', verify=False, timeout=4)

  if r.status_code == 200:
    # awesome result
    data = r.json()
    
    currentF = float(data["StatusSNS"]["ENERGY"]["Current"])
    current = int(currentF * 1000)
    timestamp = data["StatusSNS"]["Time"]
    
    print( "Measurement {0}: {1} mA".format(timestamp, current) )

    handleCurrentCurrent(timestamp, current, prevValue)
  else:
    print( "Request not successful" )

  # call this every three seconds, with the current val as prev value
  threading.Timer(3.0, fetchCurrent, [current]).start()

def fetchSysMon():
  if _influxUrl == None:
    return

  r = requests.get(_sysmonUrl + '/getsys', verify=False, timeout=4)

  if r.status_code == 200:
    # awesome result
    data = r.json()

    with InfluxDBClient(url=_influxUrl, token=_token, org=_org) as client:
      write_api = client.write_api(write_options=SYNCHRONOUS)

      datastr = "sysmon,system=oCIS cpu=%s,mem=%s,netin=%s,netout=%s" % (data["cpu_p"], data["mem_p"], data["nin"], data["nout"])
      print( "datastring: %s"% datastr)
      write_api.write("sysmon", _org, datastr)
      client.close()

  threading.Timer(3.0, fetchSysMon).start()

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
threading.Timer(3.0, fetchCurrent, [0]).start()
print ("Measurement starts in a few seconds")

# start the system monitor
if _sysmonUrl != None:
  threading.Timer(3.0, fetchSysMon).start()


# Some nice lights in the ammeter device:
led(0,0,0,   0,  82)


