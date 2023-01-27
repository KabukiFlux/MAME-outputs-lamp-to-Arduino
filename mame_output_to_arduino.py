#!/usr/bin/python3
"""Test script to convert MAME network output to arduino.

This script retrieves MAME output via <ip:8000> and
maps the output to a byte lamps, the output of the lamps
will be processed and sent back to an arduino via serial
communication. This script was used for testing purposes
during a live event on:
Twitch https://www.twitch.tv/kabukiflux
"""

import sys
import socket
import serial
import serial.tools.list_ports
import time

__author__ = "KabukiFlux"
__copyright__ = "Copyright 2023, KabukiFlux"
__license__ = "MIT"
__version__ = "1.0.0"
__status__ = "Development"

# ***************** HOW TO **************************************************************
# This script will send mame commands to arduino via serial port
# 1- configure serial port below to the arduino (optional)
# 2- ensure mame.ini OSD OUTPUT OPTIONS output is set to 'network'
# 3- in output_map.json you can set the mame message for the right real output on arduino
# 4- run mame game
# 5- execute this script (use ctrl+c to close it)
# 6- if the script doesn't work check firewall rules for mame in your antivirus
# ***************************************************************************************

# You can define it, but we will use autodetect if only one serial port is available.
serial_port = 'com1'
autodetect_serial = True


class SerialArduino:
    """serial output to arduino"""
    baud_rate = 115200

    def __init__(self, serialp):
        self.serialp = serialp
        self.firstserial = self.serial_port()
        try:
            if self.firstserial is not None and autodetect_serial:
                print(f'Serial port detected: {self.firstserial}')
                self.arduino = serial.Serial(self.firstserial, SerialArduino.baud_rate)
            else:
                self.arduino = serial.Serial(self.serialp, SerialArduino.baud_rate)
        except serial.SerialException:
            sys.stderr.write('Could not open the serial port \n')
            time.sleep(1)

    def __call__(self):
        return self

    def send(self, message):
        self.arduino.write(message)

    def close(self):
        if hasattr(self, 'arduino'):
            self.arduino.close()

    def serial_port(self):
        """ Sends name for the first available serial port

            :returns:
                The first serial port or None
        """
        ports = serial.tools.list_ports.comports(include_links=False)
        available_ports = []
        for port in ports:
            try:
                if hasattr(port, 'name'):
                    s = serial.Serial(port.name)
                    s.close()
                    available_ports.append(port)
            except (serial.SerialException, KeyboardInterrupt):
                pass
        if len(available_ports) > 0:
            first_port = (available_ports[0]).name
        else:
            first_port = None
        return first_port


class NetMame:
    """read mame network messages"""

    message = b"GET / HTTP/1.1\r\n\r\n"
    mame_host = 'localhost'
    mame_port = 8000

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = socket.gethostbyname(self.mame_host)
        self.received = None
        try:
            self.connect()
            # self.socket.connect((self.ip, self.mame_port))
        except socket.error:
            sys.stderr.write('Could not connect to MAME \n')
            time.sleep(1)
        else:
            self.socket.sendall(NetMame.message)

    def __call__(self):
        return self

    def connect(self):
        connected = False
        print(f'Waiting for MAME network output')
        while not connected:
            try:
                self.socket.connect((self.ip, self.mame_port))
                connected = True
            except KeyboardInterrupt:
                sys.stderr.write('Closing app \n')
                break
            except (socket.error, ConnectionResetError):
                time.sleep(1)

    def read(self):
        try:
            self.received = self.socket.recv(4096)
        except KeyboardInterrupt:
            self.received = None
        return self.received

    def close(self):
        if hasattr(self, 'socket'):
            self.socket.close()


class OutputFromNetResponse:
    """message parser and mapper"""

    import json
    f = open('output_map.json', "r")
    # Reading from JSON file including dictionary mappings
    texts_from_net_json = json.loads(f.read())
    # UNUSED SAMPLE FOR JSON
    texts_from_net = \
        {
            # Outrun
            'Start_lamp': 0,  # yellow lamp
            'Brake_lamp': 2,  # red lamp
        }
    output_mappings = texts_from_net_json['defaults']

    def __init__(self):
        self.lamps = 0

    def set_bit(self, bit_n):
        self.lamps = self.lamps | (1 << bit_n)

    def clear_bit(self, bit_n):
        self.lamps = self.lamps & ~(1 << bit_n)

    def get_lamp_bit(self, key):
        # returns the bit, understands mame byte strings
        return self.output_mappings.get(key.decode('ascii'))

    def getlampchange(self, mame_message):
        lines = mame_message.split(b'\r', -1)
        for line in lines:
            # translate message to lamps
            output_selected = line.split(b' = ')
            if len(output_selected) >= 2:
                if output_selected[0] == b'mame_start':
                    self.gameOverrideOutputs(output_selected[1])
                # translate message to lamps
                # print(f'OUT_M: {output_selected[0]} -> {output_selected[1]}')
                bit = self.get_lamp_bit(output_selected[0])
                if bit is not None:
                    if output_selected[1] == b'1':
                        self.set_bit(bit)
                    if output_selected[1] == b'0':
                        self.clear_bit(bit)
        # Return lamps as int
        return self.lamps

    def gameOverrideOutputs(self, game):
        game = game.decode('ascii')
        if self.texts_from_net_json.get(game) is not None:
            self.output_mappings = self.texts_from_net_json[game]
            print(f'Special mappings detected for this game {self.output_mappings}')
        else:
            self.output_mappings = self.texts_from_net_json['defaults']
            print(f'Mappings reverted to default')

    def getlampbyte(self):
        # Return lamps as one BYTE ready for serial output
        return self.lamps.to_bytes(1, byteorder='big', signed=False)

    def getlampdisplay(self):
        # Return lamps as one BYTE string to print in console
        return "{0:08b}".format(self.lamps)

if __name__ == '__main__':  # noqa
    arduino = SerialArduino(serial_port)
    mame = None
    try:
        mame = NetMame()
    except OSError:
        sys.stderr.write('Forced to close \n')
        sys.exit(1)
    output = OutputFromNetResponse()
    while True:
        try:
            if mame is not None:
                reply = mame.read()
                if reply is not None:
                    output.getlampchange(reply)
                    lamp_binary = output.getlampdisplay()
                    print(f'LAMPS: {lamp_binary} -> {reply}')
                    arduino.send(output.getlampbyte())
        except socket.error:
            sys.stderr.write('MAME has been closed, reconnecting \n')
            mame.close()
            del mame
            mame = NetMame()
        except KeyboardInterrupt:
            sys.stderr.write('Closing app \n')
            break
    mame.close()
    arduino.close()
