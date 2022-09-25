#!/usr/bin/python3

# Klaas Freitag <kfreitag@owncloud.com>
# distribute under GPLv2 or ask
#
# Read current from a tasmota device (power plug) and push it on to a self
# modified mechanical Ampere Meter -  Kudos Jürgen W.

import threading
import requests
import serial, sys, time

# configuration - edit here: 

# The URL of the tasmota device.
_tasmoUrl = 'http://192.168.0.102'

# maximum current in milli ampere
_maxMilliAmp = 250

# The device is supposed to provide this API:
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


# Not yet used or working - feed data to InfluxDB
def toInflux(timestamp, current):
  
  # You can generate a Token from the "Tokens Tab" in the UI
  token = "kYwjpIN2lvYxv6usfbKub1pcDF559TstbSvIdJXR91NwqCbtk9Np38206K2YKpQrrcsmZm_0_ShQN6Lxf-kk6w=="
  org = "ownCloud"
  bucket = "ocis1"

  write_api = client.write_api(write_options=SYNCHRONOUS)

  data = "mem,host=host1 used_percent=23.43234543"
  write_api.write(bucket, org, data)
  client = InfluxDBClient(url="http://localhost:8086", token=token)

def fetchCurrent():
  # call this every three seconds
  threading.Timer(3.0, fetchCurrent).start()
  # print ("Fetching Current!")
  
  r = requests.get(_tasmoUrl + '/cm?cmnd=Status%2010')

  if r.status_code == 200:
      # awesome result
    data = r.json()
    
    currentF = float(data["StatusSNS"]["ENERGY"]["Current"])
    current = int(currentF * 1000)
    timestamp = data["StatusSNS"]["Time"]
    
    print( "XX {0}: {1}".format(timestamp, current) )
    
    toAmperemeter(current)
    # toInflux(timestamp, current)
    
    # color(percent)
  else:
    print( "Request not successful" )
  

# =====================================================================

if len(sys.argv) < 2:
  print("\nUsage: %s PORT\n\nAvailable ports are:" % sys.argv[0])

  import serial.tools.list_ports as L

  for p in map(lambda x: x.device, L.comports()):
     print("  " + p)
  print("\n")
  sys.exit(1)

ser = serial.Serial(sys.argv[1], baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)

led(0,0,0,   0,  82)
# led(0,20,0, 26, 28)

# led(10,20,20, 9, 25)

# Start the timer here:
fetchCurrent()


