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

id_counter = 0x300

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


def gui_thread():
    root = tk.Tk()
    root.title("G30")
    root.mainloop()

# Start the GUI thread
gui_thread = threading.Thread(target=gui_thread)
gui_thread.start()

def receive():
    while True:
        message = bus.recv()

        #print(message)

receive = threading.Thread(target=receive)    
receive.start()


while True:
    current_time = time.time()
    
    #read from the socket if there is data to be read
    #i have no idea how it works, i just know it works
    ready_to_read, _, _ = select.select([sock], [], [], 0)
    if sock in ready_to_read:
        data, _ = sock.recvfrom(256)
        # I4sHc2c7f2I3f16s16si
        packet = struct.unpack('2c7f2I3f', data)
        rpm = int(max(min(packet[3], 8000), 0))
        speed = packet[2] #convert speed to km/h
        coolant_temp = int(packet[5])
        oil_temp = int(packet[8])
        fuel = int(packet[6]*100)
        gearSelector = packet[0]
        gear = packet[1]
        boost = packet[4]
        shiftlight = False
        reverse = False
        left_directional = False
        right_directional = False
        highbeam = False
        abs_active = False
        abs_fault = False
        battery = False
        tc_active = False
        tc_off = False
        cruise_control_active = False
        handbrake = False
        shiftlight = False
        ignition = False
        lowpressure = False
        check_engine = False
        foglight = False
        lowbeam = False
        
        if (packet[10]>>0)&1:
            shiftlight = True
        if (packet[10]>>1)&1:
            highbeam = True
        if (packet[10]>>2)&1:
            handbrake = True
        if (packet[10]>>4)&1:
            tc_active = True
        if (packet[10]>>5)&1:
            tc_off = True
        if (packet[10]>>6)&1:
            left_directional = True
        if (packet[10]>>7)&1:
            right_directional = True
        if (packet[10]>>8)&1:
            lowoilpressure = True
        if (packet[10]>>9)&1:
            battery = True
        if (packet[10]>>10)&1:
            abs_active = True
        if (packet[10]>>11)&1:
            abs_fault = True
        if (packet[10]>>12)&1:
            ignition = True
        if (packet[10]>>13)&1:
            lowpressure = True
        if (packet[10]>>14)&1:
            check_engine = True
        if (packet[10]>>15)&1:
            foglight = True
        if (packet[10]>>16)&1:
            lowbeam = True
        if (packet[10]>>17)&1:
            cruise_control_active = True

        #print(bc)
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
            can.Message(arbitration_id=0x105, data=[ # Speed
                0x00,0,int(speed*2),0,0,int(speed*2),0,0], is_extended_id=False),
            can.Message(arbitration_id=0x6b5, data=[ # Oil Temp
                0,0,0,0,0,128 + int((oil_temp*(9/5)+32 - 155) * (80 - 1) / (300 - 155) + 1),0,0], is_extended_id=False),
            can.Message(arbitration_id=0x522, data=[ # CEL, Oil Pressure, Coolant Temp
                0,0,0,0,(int(boost*1.75)&0b111111)<<2,int(coolant_temp*1.75)&0xf,0x10,0], is_extended_id=False),
            can.Message(arbitration_id=0x677, data=[ # drivemode, outside temp
                0,0,0,0,0,0,210,0], is_extended_id=False),
            can.Message(arbitration_id=id_counter, data=[
                random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255)], is_extended_id=False),
        ]
        
        #Update checksums and counters here
        counter_4bit = (counter_4bit + 1) % 16

        # Send Messages
        for message in messages_100ms:
            bus.send(message)
            #print(message)
            #if message.arbitration_id == 0x1ee:
            #    print(message)
            wpt.sleep(0.001)
        start_time_100ms = time.time()


    # Execute code every 10ms
    elapsed_time_10ms = current_time - start_time_10ms
    if elapsed_time_10ms >= 0.01:  # 10ms
        messages_10ms = [
            can.Message(arbitration_id=0x3a3, data=[ # RPM
                0,0,int(rpm/3)&0xff,int(rpm/3)>>8,0,0,0,0], is_extended_id=False),    
            
        ]
        #do checksums here

        for message in messages_10ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_10ms = time.time()

    # Execute code every 5s
    elapsed_time_5s = current_time - start_time_5s
    if elapsed_time_5s >= 3:
        id_counter += 1
        print(hex(id_counter))
        if id_counter == 0x7ff:
            id_counter = 0

        start_time_5s = time.time()

send_thread_20ms.join()

sock.close()

