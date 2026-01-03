# Growatt SPF Modbus

## Overview

**growattSPFModbus** exposes API to get config and values exposed via Modbus RS485 RTU Protocol.

As hardware I use RaspberryPi Zero2W and connect to iverter via USB cable.

Http server is implemented in python using Flask and accessing inverter via pymodbus module.

### Supported devices

  - Growatt SPF 3500 ES
  - Growatt SPF 5000 ES

## Run

### Prepare

Connect USB cable to port **/dev/ttyUSB0**.

Install python libraries: 
```
pip install wheel gunicorn flask flask_httpauth RPi.GPIO pymodbus pyserial
```
In case of errors force older pymodbus version
```
pip3 install --force-reinstall -v "pymodbus==3.7.4"
```

To access Serial port add run user to group **dialout** with udev rules.

Create **users.txt** to setup Basic auth.
```
user1 passwd1
```

Create **actions** folder with **sendnotification.sh** script to handle errors form server.
Example for Domoticz:
```
/usr/bin/curl -H 'Authorization: Basic XXX' "http://192.168.1.100/json.htm?type=command&param=sendnotification&subject=$1&body=$2"
```

Example to run with gunicorn:

wsgi.py
```
from growatt import app

if __name__ == "__main__":
    app.run()
```

gunicorn.conf.py
```
bind = '0.0.0.0:${SERVER_PORT}'
workers = 1
loglevel = 'debug'
accesslog = './logs/access.log'
errorlog = './logs/error.log'
capture_output = True
```

### Run
Test run with 
```
gunicorn wsgi:app
```

## API Reference

| method | path | Description | payload |
|----------|------------|------------|------------|
| GET | /growatt/config | Get inverter configuration |  |
| GET | /growatt/status | Get current exported inverter values |  |
| GET | /gpio/$pinid/high | Set RPi GPIO pin to HIGH |  |
| GET | /gpio/$pinid/low | Set RPi GPIO pin to LOW |  |


## License

This project is licensed under the **MIT License**. Feel free to use it and modify it on your own fork.

## Contributing

Pull requests with fixes are welcome! New functionalities and extensions will be not discussed in this repository.
