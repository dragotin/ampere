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

# Setup System Monitoring

This repository contains a small utility `sysmon.py` that collect some basic information about the system state of a test system. That is memory consumption, cpu utilization and network traffic. Obviously that has to be started on the system to test, ie. the Raspberry.

`sysmon.py` has a small REST interface that can be polled by the ampere script to collect system data and put them in a InfluxDB bucket. For that, a bucket called `sysmon` has to be created in the InfluxDB.

To run sysmon.py, two packages have to be installed:
`sudo apt install python3-flask python3-psutil`

# Setup k6 based Test

## cdperf

cdperf is only used to provide the tests. The cdperf script itself is not used here.

1. Clone cdperf
2. `yarn build`

-> tests are in the `tests` directory.

## Install k6

Download rpm from https://dl.k6.io/rpm/

Install the rpm: `sudo rpm -Uhv ~/downloads/k6-v0.40.0-amd64.rpm`

Run tests, for example with:
`CLOUD_HOST=https://odroidhc4:9200 k6 run --duration=20s ./tests/cdperf/issue-github-ocis-1018-propfind-flat-1000-files.js`


# Setup the Odroids

## Ubuntu 22.04 LTS

Ubuntu 22.04 LTS is used as a test OS.

### Installation

Installed via net install in Petitboot which is preinstalled on the odroids. 

To do that, perform the following steps:

1. Boot into Petitboot
2. Leave Petitboot with `exit to shell`
3. Enter the command `udhcpc`
4. Enter the command `netboot-default`
5. `exit` to go back to the Petitboot. Now there should be installation options.

If the list of installation options remains empty, repeat the steps until they appear.

### Additional Packages

The following extra packages have to be installed:
- openssh-server for SSH access
    - `sudo apt install openssh-server`
    - `sudo systemctl status ssh` to check the status
    - `sudo ufw allow ssh` to open the firewall
- docker (if needed)
    - `sudo apt install docker.io`
    - Add the user to the docker group: `sudo usermod -aG docker $USER`
    - Reload groups: `newgrp docker`
    - Check the install: `docker run hello-world`
- docker-compose
    - `sudo apt install docker-compose`



## Setup Docker

`curl -fsSL https://get.docker.com -o get-docker.sh`
`DRY_RUN=1 sh ./get-docker.sh`
`sudo apt-get install docker-compose`

# Two test hosts

## odroidnc - Test host for nextcloud

# Setup ODroid HC4

see https://www.armbian.com/odroid-hc4/

