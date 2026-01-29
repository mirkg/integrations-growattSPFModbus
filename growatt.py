#!/usr/bin/env python3

import time
import logging
import urllib
import subprocess
import atexit
import sys

import RPi.GPIO as GPIO

from flask import Flask, jsonify
from flask_httpauth import HTTPBasicAuth

from pymodbus.exceptions import ModbusIOException
from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus import FramerType

USB_PORT = "/dev/ttyUSB0"

class GrowattClient:
    def __init__(self, client):
        self.client = client

        row = self.client.read_holding_registers(73)
        if type(row) is ModbusIOException:
            raise row
        self.modbusVersion = row.registers[0]

    # Codes
    StatusCodes = {
        0: "Standby",
        1: "noUSE",
        2: "Discharge",
        3: "Fault",
        4: "Flash",
        5: "PV Charge",
        6: "AC Charge",
        7: "Combine Charge",
        8: "Combine charge and Bypass",
        9: "PV charge and Bypass",
        10: "AC Charge and Bypass",
        11: "Bypass",
        12: "PV charge and discharge"
    }

    def readConfig(self):
        row = self.client.read_holding_registers(0, 81)
        info = {                                                        # ==================================================================
            "StatusCode": row.registers[0],                             # 0000 off,outputon 0001 on,outen 0100 off/disa 0101 on,disa
            "OutputConfig": row.registers[1],                           # 0 bat first, 1 pv first, 2 uti first
            "ChargeConfig": row.registers[2],                           # 0 PV first, 1 pv&uti, 2 PV only
            "UtiOutStart": row.registers[3],                            # 0-23 (Hours)
            "UtiOutEnd": row.registers[4],                              # 0-23 (Hours)
            "UtiChargeStart": row.registers[5],                         # 0-23 (Hours)
            "UtiChargeEnd": row.registers[6],                           # 0-23 (Hours)
            "PVmodel": row.registers[7],                                # 0 independent, 1 parallel
            "ACInModel": row.registers[8],                              # 0 APL,90-280vac UPS 170-280vac
            "FwVersionH": row.registers[9],                             #
            "FwVersionM": row.registers[10],                            #
            "FwVersionL": row.registers[11],                            #
            "FwVersion2H": row.registers[12],                             #
            "FwVersion2M": row.registers[13],                            #
            "FwVersion2L": row.registers[14],                            #
            "OutputVoltType": row.registers[18],                           #0:208, 1:230, 2:240
            "OutputFreqType": row.registers[19],                           #0:50hz 1:60hz
            "OverLoadRestart": row.registers[20],                           #0yes, 1 no, 2switch to uti
            "OverTempRestart": row.registers[21],                           #0yes, 1 no
            "BuzzerEN": row.registers[22],                           #0 no,1 yes,
            "Serno5": row.registers[23],                           #
            "Serno4": row.registers[24],                           #
            "Serno3": row.registers[25],                           #
            "Serno2": row.registers[26],                           #
            "Serno1": row.registers[27],                           #
            "MoudleH": row.registers[28],                           #
            "MoudleL": row.registers[29],                           #P0 lead, 1 lithium, 2 customlead  User 0 no, 1growatt, 2cps, 3haiti M 3kw 5kw, Saging 0 norm/1aging
            "ComAddress": row.registers[30],                           #1-254
            "FlashStart": row.registers[31],                           #0001-own, 0100 control board
            "MaxChargeCurr": row.registers[34],                           #10-130
            "BulkChargeVolt": float(row.registers[35]) / 10,            #.1v 500-580
            "FloatChargeVolt": float(row.registers[36]) / 10,            #.1v 500-560
            "BatLowtoUtiVolt": float(row.registers[37]) / 10,            #.1v 444-514
            "FloatChargeCurr": float(row.registers[38]) / 10,            #.1a 0-80
            "BatteryType": row.registers[39],                           #0 lead acid, 1 lithium, 2 customLead
            "Aging Mode": row.registers[40],                           #0 normal, 1 aging mode
            "DTC": row.registers[43],                           #&*6
            "SysYear": row.registers[45],                           #
            "SysMonth": row.registers[46],                           #
            "SysDay": row.registers[47],                           #
            "SysHour": row.registers[48],                           #
            "SysMin": row.registers[49],                           #
            "SysSec": row.registers[50],                           #
            "FWBuild4": row.registers[67],                           #
            "FWBuild3": row.registers[68],                           #
            "FWBuild2": row.registers[69],                           #
            "FWBuild1": row.registers[70],                           #
            "SysWeekly": row.registers[72],                           #0-6
            "RateWattH": float(row.registers[76]) / 10,               # 0.1w
            "RateWattL": float(row.registers[77]) / 10,               # 0.1w
            "RateVAH": float(row.registers[78]) / 10,               # 0.1w
            "RateVAL": float(row.registers[79]) / 10,               # 0.1w
            "Factory": row.registers[80]                           #ODM Info Code
        }
        return info

    def readData(self):
        row = self.client.read_input_registers(0, 83)
        info = {                                    # ==================================================================
            "StatusCode": row.registers[0],         # N/A,      Inverter Status,    Inverter run state
            "Status": self.StatusCodes[row.registers[0]],
            "Vpv1": float(row.registers[1]) / 10,               # 0.1V,     PV1 voltage
            "Vpv2": float(row.registers[2]) / 10,               # 0.1V,     PV2 voltage
            "Ppv1H": float(row.registers[3]) / 10,              # 0.1W,     PV1 Charge power (high)
            "Ppv1L": float(row.registers[4]) / 10,              # 0.1W,     PV1 Charge power (low) 
            "Ppv2H": float(row.registers[5]) / 10,              # 0.1W,     PV2 Charge power (high)
            "Ppv2L": float(row.registers[6]) / 10,              # 0.1W,     PV2 Charge power (low)
            "Buck1Curr": float(row.registers[7]) / 10,          # 0.1A,     Buck1 current
            "Buck2Curr": float(row.registers[8]) / 10,          # 0.1A,     Buck2 current
            "OPWattH": float(row.registers[9]) / 10,            # 0.1W,     Output active power (high)
            "OPWattL": float(row.registers[10]) / 10,           # 0.1W,     Output active power (low)
            "OPVAH": float(row.registers[11]) / 10,             # 0.1VA     Output apparent power (high)
            "OPVAL": float(row.registers[12]) / 10,             #
            "ACChrWattH": float(row.registers[13]) / 10,        # 0.1W,     AC Charge Watts (high)
            "ACChrWattL": float(row.registers[14]) / 10,        #
            "ACChrVAH": float(row.registers[15]) / 10,          # 0.1VA,    AC Charge apparent power (high)
            "ACChrVAL": float(row.registers[16]) / 10,          #
            "BatVolt": float(row.registers[17]) / 100,          # 0.01V,    Battery Voltage
            "BatterySOC": float(row.registers[18]) / 1,         # 1%,       Battery State of Charge
            "BusVolt": float(row.registers[19]) / 10,           # 0.1V,     Bus Voltage
            "GridVolt": float(row.registers[20]) / 10,          # 0.1V,     AC input Voltage
            "LineFreq": float(row.registers[21]) / 100,         # 0.01Hz,   AC input Freq
            "OutputVolt": float(row.registers[22]) / 10,        # 0.1V,     AC Output Voltage
            "OutputFreq": float(row.registers[23]) / 100,       # 0.01Hz    AC Output Freq
            "OutputDCV": float(row.registers[24]) / 10,         # 0.1V      DC Output Voltage
            "InvTemp": float(row.registers[25]) / 10,           # 0.1C      Inverter Temp
            "DCDCTemp": float(row.registers[26]) / 10,          # 0.1C      DCDC Temp
            "LoadPercent": float(row.registers[27]) / 10,       # 0.1%      Inverter Load Percent
            "BatdsppV": float(row.registers[28]) / 100,         # 0.01V     Battery-port volt (DSP)
            "BatdspbV": float(row.registers[29]) / 100,         # 0.01V     Battery-bus voltage (DSP)
            "TimeTotalH": float(row.registers[30]) / 2,         # 0.5S,     Time total H,       Work time total (high)
            "TimeTotalL": float(row.registers[31]) / 2,         # 0.5S,     Time total L,       Work time total (low)
            "Buck1Temp": float(row.registers[32]) / 10,         # 0.1C,     Temperature,        Inverter temperature
            "Buck2Temp": float(row.registers[33]) / 10,         # 0.1C,     Temperature,        Inverter temperature
            "OPCurr": float(row.registers[34]) / 10,            # 0.1A,     Output Current
            "InvCurr": float(row.registers[35]) / 10,           # 0.1A,     Inv Current
            "ACInWattH": float(row.registers[36]) / 10,         # 0.1W,     AC Input watt (high)
            "ACInWattL": float(row.registers[37]) / 10,         # 0.1W,     AC Input watt (low)
            "ACInVAH": float(row.registers[38]) / 10,           # 0.1A,     AC Input VA (high)
            "ACInVAL": float(row.registers[39]) / 10,           # 0.1A,     AC Input VA (low)
            "Faultbit": float(row.registers[40]),               # &*1
            "Warnbit": float(row.registers[41]),                # &*1
            "Faultvalue": float(row.registers[42]),             # fault value
            "Warnvalue": float(row.registers[43]),              # warn value
            "DTC": float(row.registers[44]),                    #
            "CheckStep": float(row.registers[45]),              #
            "ProductionLM": float(row.registers[46]),           #
            "ConstPOKF": float(row.registers[47]),              # Constant power ok flag (0 no, 1 OK)
            "Epv1todayH": float(row.registers[48]) / 10,        # 0.1kWh,   Energy today H,     Today generate energy (high)
            "Epv1todayL": float(row.registers[49]) / 10,        # 0.1kWh,   Energy today l,     Today generate energy (low)
            "Epv1totalH": float(row.registers[50]) / 10,        # 0.1kWh,   Energy total H,     generate energy total (high)
            "Epv1totalL": float(row.registers[51]) / 10,        # 0.1kWh,   Energy total l,     generate energy total (low)
            "Epv2todayH": float(row.registers[52]) / 10,        # 0.1kWh,   Energy today H,     Today generate energy (high)
            "Epv2todayL": float(row.registers[53]) / 10,        # 0.1kWh,   Energy today l,     Today generate energy (low)
            "Epv2totalH": float(row.registers[54]) / 10,        # 0.1kWh,   Energy total H,     generate energy total (high)
            "Epv2totalL": float(row.registers[55]) / 10,        # 0.1kWh,   Energy total l,     generate energy total (low)
            "EacchrtodayH": float(row.registers[56]) / 10,      # 0.1kWh,   AC charge Energy Today (high)
            "EacchrtodayL": float(row.registers[57]) / 10,      # 0.1kWh,   AC charge Energy Todat (low)
            "EacchrtotalH": float(row.registers[58]) / 10,      # 0.1kWh,   AC charge Energy Total (high)
            "EacchrtotalL": float(row.registers[59]) / 10,      # 0.1kWh,   AC charge Energy Total (low)
            "EbatchrtodayH": float(row.registers[60]) / 10,     # 0.1kWh,   Bat discharge Energy Today (high)
            "EbatchrtodayL": float(row.registers[61]) / 10,     # 0.1kWh,   Bat discharge Energy Todat (low)
            "EbatchrtotalH": float(row.registers[62]) / 10,     # 0.1kWh,   Bat discharge Energy Total (high)
            "EbatchrtotalL": float(row.registers[63]) / 10,     # 0.1kWh,   Bat discharge Energy Total (low)
            "EacdischrtodayH": float(row.registers[64]) / 10,   # 0.1kWh,   AC discharge Energy Today (high)
            "EacdischrtodayL": float(row.registers[65]) / 10,   # 0.1kWh,   AC discharge Energy Todat (low)
            "EacdischrtotalH": float(row.registers[66]) / 10,   # 0.1kWh,   AC discharge Energy Total (high)
            "EacdischrtotalL": float(row.registers[67]) / 10,   # 0.1kWh,   AC discharge Energy Total (low)
            "Acchrcurr": float(row.registers[68]) / 10,         # 0.1A,     AC Charge Battery Current
            "ACdischrwattH": float(row.registers[69]) / 10,     # 0.1W,     AC discharge watt (high)
            "ACdischrwattL": float(row.registers[70]) / 10,     # 0.1W,     AC discharge watt (low)
            "ACdischrvaH": float(row.registers[71]) / 10,       # 0.1VA     AC discharge va (high)
            "ACdischrvaL": float(row.registers[72]) / 10,       # 0.1VA     AC discharge va (low)
            "BatdischrwattH": float(row.registers[73]) / 10,    # 0.1W      Bat discharge watts (high)
            "BatdischrwattL": float(row.registers[74]) / 10,    # 0.1W      Bat discharge watts (low)
            "BatdischrvaH": float(row.registers[75]) / 10,      # 0.1VA     Bat discharge va (high)
            "BatdischrvaL": float(row.registers[76]) / 10,      # 0.1VA     Bat discharge va (low)
            "BatwattH": float(row.registers[77]) / 10,          # 0.1W      Signed int positive discharge, negative battery charge power
            "BatwattL": float(row.registers[78]) / 10,          # 0.1W      Signed int positive discharge, negative battery charge power
            "Batovercharge": float(row.registers[80]),          # 0 no, 1 yes
            "Mpptfanspeed": float(row.registers[81]),           # 1%        Fan speed of MPPT Charger
            "Invfanspeed": float(row.registers[82]),            # 1%        Fan speed of Inverter
        }
        return info

pin16 = 16

app = Flask(__name__)
auth = HTTPBasicAuth()

client = None
growatt = None

users = {}

def connect():
    global growatt
    try:
        client = ModbusClient(framer=FramerType.RTU, port=USB_PORT, baudrate=9600, stopbits=1, parity='N', bytesize=8, timeout=1)
        client.connect()
        growatt = GrowattClient(client)
        app.logger.error('Connected to Inverter')
        exec_action('sendnotification', ['growatt_connected', urllib.parse.quote_plus(str(int(time.time())))])
    except Exception as ex:
        app.logger.error('Connecting to Inverter Failed=[' + str(ex) + ']')
        exec_action('sendnotification', ['growatt_connection_failed', urllib.parse.quote_plus(str(ex))])
        sys.exit(1)

def configure():
    with open('users.txt') as file:
        for line in file:
            if line[0] != '#':
                users[line.strip().split(' ')[0]] = line.strip().split(' ')[1]
    app.logger.error(users.keys())


@auth.verify_password
def verify_password(username, password):
    if username in users and users.get(username) == password:
        return username


@app.route("/")
def hello():
    return jsonify({'resp': 'hello :)'})

@app.route("/gpio/<pin>/high")
@auth.login_required
def gpio_high(pin):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(int(pin), GPIO.OUT)
    GPIO.output(int(pin), True)
    app.logger.error('set pin:' + pin)
    return jsonify({'resp': 'set pin:' + pin})

@app.route("/gpio/<pin>/low")
@auth.login_required
def gpio_low(pin):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(int(pin), GPIO.OUT)
    GPIO.output(int(pin), False)
    app.logger.error('unset pin:' + pin)
    return jsonify({'resp': 'unset pin:' + pin})

@app.route("/growatt/config")
@auth.login_required
def getconfig():
    try:
        points = {
            'time': int(time.time()),
            "data": growatt.readConfig()
        }
        return jsonify(points)
    except Exception as ex:
        app.logger.error('failed: config with output=[' + str(ex) + ']')
        exec_action('sendnotification', ['growatt_config_failed', urllib.parse.quote_plus(str(ex))])
        return jsonify({'resp': 'config failed', 'error': str(ex)})

@app.route("/growatt/status")
@auth.login_required
def getstatus():
    try:
        points = {
            'time': int(time.time()),
            "data": growatt.readData()
        }
        return jsonify(points)
    except Exception as ex:
        app.logger.error('failed: status with output=[' + str(ex) + ']')
        exec_action('sendnotification', ['growatt_status_failed', urllib.parse.quote_plus(str(ex))])
        return jsonify({'resp': 'status failed', 'error': str(ex)})

def exec_action(action, args):
    try:
        cmd = '/home/pi/servers/growatt/actions/' + action + '.sh'
        for arg in args:
            cmd += ' ' + arg
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        app.logger.info('executed: ' + action + ' with output=[' + str(output) + ']')
    except subprocess.CalledProcessError as ex:
        app.logger.error('failed: ' + action +  ' with output=[' + str(ex.output) + ']')

def on_exit():
    GPIO.cleanup()

if __name__ == "__main__":
    configure()
    connect()
    atexit.register(on_exit)
    app.run(host='0.0.0.0')
else:
    configure()
    connect()
    atexit.register(on_exit)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
