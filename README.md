# Ampere Measure

Start the script `ampere.py` after having configured the power plug URL and the maximum
expected current in the script. It takes the device file of the Amperemeter, ie. `/dev/ttyUSB0`.

Status:
- it is working with a Gosund SP1 with Tansmota Firmware power plug. It is harvesting data from the power plug through WLAN - and moving the pointer of the Amperemeter accordingly.
- LED light is not yet properly set according to the current.

# Setup InfluxDB

Feeding the data into an InfluxDB to visualize over time with Grafana & friends: Not yet working.

Folling this: https://medium.com/geekculture/deploying-influxdb-2-0-using-docker-6334ced65b6c

- Install InfluxDB via docker: `docker pull influxdb:2.0.7`
- Create a config file: `docker run --rm influxdb:2.0.7 influxd print-config > config.yml`
- Create DB directory: `mkdir influxdb2`
- Run influxDB Docker: `docker run --name influxdb -d -p 8086:8086 --volume `pwd`/influxdb2:/var/lib/influxdb2 --volume `pwd`/config.yml:/etc/influxdb2/config.yml influxdb:2.0.7`
- Setup a bucket and stuff: `docker exec influxdb influx setup --bucket ocis1 --org ownCloud --password 123456 --username owncloud --force`

Goto http://localhost:8086 to configure stuff.
