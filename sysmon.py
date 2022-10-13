#!/usr/bin/python3

import os
import time
import psutil
from flask import Flask, jsonify, request

app = Flask(__name__)
@app.route('/getuser', methods=['GET'])

def getusers():
     userlist = []
     userlist = psutil.users()
     return jsonify(userlist)

@app.route('/getmem', methods=['GET'])

def getmem():
    return jsonify(psutil.virtual_memory().percent)

@app.route('/getcpu', methods=['GET'])

def getcpu():
    return jsonify(psutil.cpu_percent(interval=2))

@app.route('/getsys', methods=['GET'])

def getsys():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    inf = 'eth0'
    net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[inf]
    net_in_1 = net_stat.bytes_recv
    net_out_1 = net_stat.bytes_sent
    time.sleep(1)
    net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[inf]
    net_in_2 = net_stat.bytes_recv
    net_out_2 = net_stat.bytes_sent

    net_in = round((net_in_2 - net_in_1) / 1024 / 1024, 3)
    net_out = round((net_out_2 - net_out_1) / 1024 / 1024, 3)

    return jsonify( cpu_p = cpu, mem_p = mem, nin = net_in, nout = net_out)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

