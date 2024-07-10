import time
import can
import random 
import socket
import struct
import select 
import threading
import tkinter as tk
import win_precise_time as wpt
from datetime import datetime

bus = can.interface.Bus(channel='com7', bustype='seeedstudio', bitrate=500000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 4567))
    
# Track time for each function separately
start_time_100ms = time.time()
start_time_10ms = time.time()
start_time_5s = time.time()

id_counter = 0x640
counter_4bit = 0

ignition = True
rpm = 780
speed = 0
gear = b'0'
gearSelector = b"P"
coolant_temp = 90
oil_temp = 90
fuel = 100
boost = 0
drive_mode = 2

left_directional = False
lowpressure = False
right_directional = False
tc_off = False
tc_active = False
abs = False
cruise_control_active = False
battery = False
handbrake = False
reverse = False
highbeam = False
outside_temp = 72

foglight = False
rear_foglight = False
lowbeam = False 
check_engine = False
hood = False
trunk = False

airbag = False
seatbelt = False

# Global variable for steering wheel control data
steering_wheel_data = [0, 0, 0]

def gui_thread():
    def set_steering_wheel_data(data):
        global steering_wheel_data
        steering_wheel_data = data

    def reset_steering_wheel_data(event):
        global steering_wheel_data
        steering_wheel_data = [0, 0, random.randint(0,255)]

    root = tk.Tk()
    root.title("G30")

    button_up = tk.Button(root, text="Up")
    button_up.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0x12, 0x00, 0x01]))
    button_up.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_up.pack()

    button_ok = tk.Button(root, text="OK")
    button_ok.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0x00, 0x13, 0x10]))
    button_ok.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_ok.pack()

    button_down = tk.Button(root, text="Down")
    button_down.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0x12, 0x00, 0x0F]))
    button_down.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_down.pack()

    button_return = tk.Button(root, text="Return")
    button_return.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0x03, 0x13, 0x01]))
    button_return.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_return.pack()

    root.mainloop()

# Start the GUI thread
gui_thread = threading.Thread(target=gui_thread)
gui_thread.start()

def receive():
    while True:
        message = bus.recv()

receive_thread = threading.Thread(target=receive)    
receive_thread.start()

while True:
    current_time = time.time()
    
    # Read from the socket if there is data to be read
    ready_to_read, _, _ = select.select([sock], [], [], 0)
    if sock in ready_to_read:
        data, _ = sock.recvfrom(256)
        packet = struct.unpack('2c7f2I3f', data)
        rpm = int(max(min(packet[3], 8000), 0))
        speed = packet[2] # Convert speed to km/h
        coolant_temp = int(packet[5])
        oil_temp = int(packet[8])
        fuel = int(packet[6]*100)
        gearSelector = packet[0]
        gear = packet[1]
        boost = packet[4]
        
        # Parse other packet data (bitwise operations)
        shiftlight = (packet[10]>>0) & 1
        highbeam = (packet[10]>>1) & 1
        handbrake = (packet[10]>>2) & 1
        tc_active = (packet[10]>>4) & 1
        tc_off = (packet[10]>>5) & 1
        left_directional = (packet[10]>>6) & 1
        right_directional = (packet[10]>>7) & 1
        lowoilpressure = (packet[10]>>8) & 1
        battery = (packet[10]>>9) & 1
        abs_active = (packet[10]>>10) & 1
        abs_fault = (packet[10]>>11) & 1
        ignition = (packet[10]>>12) & 1
        lowpressure = (packet[10]>>13) & 1
        check_engine = (packet[10]>>14) & 1
        foglight = (packet[10]>>15) & 1
        lowbeam = (packet[10]>>16) & 1
        cruise_control_active = (packet[10]>>17) & 1
    
    # Send each message every 100ms
    elapsed_time_100ms = current_time - start_time_100ms
    if elapsed_time_100ms >= 0.1:
        date = datetime.now()
        match gear:
            case b'\x00':
                gearByte = 0x60
            case b'\xff':
                gearByte = 0x70
            case _:
                gearByte = int.from_bytes(gear, "big")

        messages_100ms = [
            can.Message(arbitration_id=0x3c0, data=[ # Ignition
                0,0,0x03,0], is_extended_id=False),
            can.Message(arbitration_id=0x310, data=[ # Gear
                gearByte,0x50,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x662, data=[ # Lighting
                0x00,0,0b00000011,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x663, data=[ # Alternator and voltage
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x105, data=[ # Speed
                0x00,0,int(speed*2),0,0,int(speed*2),0,0], is_extended_id=False),
            can.Message(arbitration_id=0x6b5, data=[ # Oil Temp
                0,0,0,0,0,128 + int((oil_temp*(9/5)+32 - 155) * (80 - 1) / (300 - 155) + 1),0,0], is_extended_id=False),
            can.Message(arbitration_id=0x522, data=[ # CEL, Oil Pressure, Coolant Temp
                0,0,0,0,(int(boost*1.75)&0b111111)<<2,min(int(coolant_temp*2),255),0x10,0], is_extended_id=False),
            can.Message(arbitration_id=0x677, data=[ # drivemode, outside temp
                0,0,0,0,0,0,210,0], is_extended_id=False),
            can.Message(arbitration_id=0x5bf, data=steering_wheel_data, is_extended_id=False),
            can.Message(arbitration_id=id_counter, data=[
                random.randint(0,255),random.randint(0,255),random.randint(0,255)], is_extended_id=False),
        ]
        
        # Update checksums and counters here
        counter_4bit = (counter_4bit + 1) % 16

        # Send Messages
        for message in messages_100ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_100ms = time.time()

    # Execute code every 10ms
    elapsed_time_10ms = current_time - start_time_10ms
    if elapsed_time_10ms >= 0.01:  # 10ms
        messages_10ms = [
            can.Message(arbitration_id=0x3a3, data=[ # RPM
                0,0,int(rpm/3)&0xff,int(rpm/3)>>8,0,0,0,0], is_extended_id=False),    
        ]
        # Do checksums here

        for message in messages_10ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_10ms = time.time()

    # Execute code every 5s
    elapsed_time_5s = current_time - start_time_5s
    if elapsed_time_5s >= 6:
        id_counter += 1
        print(hex(id_counter))
        if id_counter == 0x7ff:
            id_counter = 0

        start_time_5s = time.time()

receive_thread.join()

sock.close()
