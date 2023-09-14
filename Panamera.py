import can
import threading
import time
import random
import socket
import struct
import tkinter as tk

simple_counter = 0x00
random_id = 1300
send_lock = threading.Lock()

gear = b'\x02'  # 
speed = 0 # mp/h
lights = 0 # dahs lights
outside_temp = 72 # Farenheight - INACCURATE, FIX

#TPMS
fl_pressure = 31
fr_pressure = 32
rr_pressure = 14
rl_pressure = 31

#Cruise Control
cc_active = False
cc_speed = 50 # Set CC Speed
cc_speed_set = True # Is the speed set? (Yellow icon if not)

# Door status
fl_open = False
fr_open = False
rl_open = False
rr_open = False
trunk_open = False

# Power Steering
ps_light = False

# Engine
mil = False
rpm = 2000  # RPM 
engtemp = 100
oil_temp = 100
oil_press = 2.5
boost = 5 #psi

# TC, ABS, Brake
brake_light = False
tc_status = 0x0 # 0x0 = On & Inactive, 0x1 = On & Active (Blinking), 0x2 = Off
abs_light = False

# Lights
parking_lights = True
fog_lights = False
left_directional = False
right_directional = False
high_beam = False


messages_20ms = [
    (0x3a3, [0, 0, 0, 0, 0, 0, 0, 0]),

]

messages_100ms = [
    (random_id, [0,0,0,0,0,0,0,0]), # Random
    (0x3c0, [0, 0, 0x03, 0]), #Ignition
    (0x310, [0x0d,0x50,0,0,0,0,0,0]), # Gear
    (0x662, [0x00,0,0b00000011,0,0,0,0,0]), # Lighting
    (0x105, [0x00,0,0x05,0,0,0x05,0,0]), # Speed
    (0x6b5, [0,0,0,0,0,0,0,0]), # Oil Temp
    (0x522, [0,0,0,0,0,0,0,0]), # CEL, Oil Pressure, Coolant Temp
    (0x677, [0,0,0,0,0,0,210,0]), # Drive Mode, Outside Temp
    (0x5bf, [0,0,0]), # Steering Wheel Buttons
]


def send_messages_20ms(bus):
    global simple_counter
    while True:
        for message_id, data in messages_20ms:
            send_lock.acquire()
            message = can.Message(arbitration_id=message_id, data=data, is_extended_id=False)
            bus.send(message, timeout=1)
            #print("Sent message (20ms):", message)
            send_lock.release()
        #20ms logic here
        messages_20ms[0][1][2] = int(rpm/3)&0xff
        messages_20ms[0][1][3] = int(rpm/3)>>8

        time.sleep(0.02)


def send_messages_100ms(bus):
    global simple_counter
    global speed
    global oil_temp
    global engtemp
    global oil_press
    while True:
        for message_id, data in messages_100ms:
            send_lock.acquire()
            message = can.Message(arbitration_id=message_id, data=data, is_extended_id=False)
            bus.send(message, timeout=1)
            #print("Sent message (100ms):", message)
            send_lock.release()
            time.sleep(0.01)
        #100ms logic here

        messages_100ms[0] = (random_id, [0,0,0,0,0,0,0,0])
        messages_100ms[0][1][0] = simple_counter
        messages_100ms[0][1][1] = simple_counter
        messages_100ms[0][1][2] = simple_counter
        messages_100ms[0][1][3] = simple_counter
        messages_100ms[0][1][4] = simple_counter
        messages_100ms[0][1][5] = simple_counter
        messages_100ms[0][1][6] = simple_counter
        messages_100ms[0][1][7] = simple_counter
        match gear:
            case b'\x00':
                messages_100ms[2][1][1] = 0x70
            case b'\x01':
                messages_100ms[2][1][1] = 0x60
            case _:
                messages_100ms[2][1][1] = 0x50
                if int.from_bytes(gear, "big") <= 6:
                    messages_100ms[2][1][0] = int.from_bytes(gear, "big")-1
                else:
                    messages_100ms[2][1][0] = int.from_bytes(gear, "big")+1

        #Speed
        print(messages_100ms[0])
        messages_100ms[4][1][2] = int(speed*0.888)
        messages_100ms[4][1][5] = int(speed*0.888)

        # Oil Temp
        messages_100ms[5][1][5] = 128 + int((oil_temp*(9/5)+32 - 155) * (80 - 1) / (300 - 155) + 1)

        # Oil Pressure
        messages_100ms[6][1][6] = int((oil_press / 5) * 128)

        # Boost
        messages_100ms[6][1][4] = (int(boost*1.75)&0b111111)<<2

        # Coolant Temp
        messages_100ms[6][1][5] = int(engtemp*1.75)&0xf

        if oil_press < 0.35:
            messages_100ms[6][1][0] += 64



        if(simple_counter == 254):
            simple_counter = 0
        else:
            simple_counter+=1
        time.sleep(0.1)



def receive_messages(bus):
    while True:
        message = bus.recv()
        #print("Received message:", message)


def testing_5s_function(bus):
    global messages_100ms
    global simple_counter
    global random_id
    while True:
        #random_id += 1        
        time.sleep(5)
            
        
def bitmanage(message_pos, data_pos, bit_position, operation):
    global messages_100ms
    message = messages_100ms[message_pos][1][data_pos]
    if operation == "+":
        message |= (1 << bit_position)
    elif operation == "-":
        message &= ~(1 << bit_position)
    messages_100ms[message_pos][1][data_pos] = message
    print(f"Message: {bin(message)}")


def connect_to_game_socket():
    # Connect to the game socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 4444))

    # Receive data from the game and update variables accordingly
    while True:
        global rpm
        global speed
        global gear
        global engtemp
        global lights
        global fuel_level
        global oil_press
        global boost
        global oil_temp
        global messages_100ms
        global messages_20ms
        # Receive data.
        data, _ = sock.recvfrom(256)

        if not data:
            break  # Lost connection

        # Unpack the data.
        outgauge_pack = struct.unpack('I4sH2c7f2I3f16s16si', data)
        time_value = outgauge_pack[0]
        car = outgauge_pack[1]
        flags = outgauge_pack[2]
        gear = outgauge_pack[3]
        speed = outgauge_pack[5]*2.23694
        rpm = max(min(outgauge_pack[6], 8000), 0)
        boost = max(outgauge_pack[7]*14.5038, 0)
        engtemp = outgauge_pack[8]
        fuel_level = outgauge_pack[9]
        #oil_press = outgauge_pack[10]
        oil_temp = outgauge_pack[11]
        dashlights = outgauge_pack[12]
        lights = outgauge_pack[13]
        throttle = outgauge_pack[14]
        brake = outgauge_pack[15]
        clutch = outgauge_pack[16]
        display1 = outgauge_pack[17]
        display2 = outgauge_pack[18]
    sock.close()

def setButtonMessage(data1, data2, data3):
    messages_100ms[8] = (0x5bf, [data1, data2, data3])
# Tkinter GUI setup
root = tk.Tk()
root.title("Car Seat Control")

btn_up = tk.Button(root, text="up")
btn_up.bind('<ButtonPress-1>', lambda event: setButtonMessage(0x12, 0x00, 0x01))
btn_up.bind('<ButtonRelease-1>', lambda event: setButtonMessage(0, 0, 0))

btn_down = tk.Button(root, text="down")
btn_down.bind('<ButtonPress-1>', lambda event: setButtonMessage(0x12, 0x00, 0x0F))
btn_down.bind('<ButtonRelease-1>', lambda event: setButtonMessage(0, 0, 0))

btn_forward = tk.Button(root, text="Return")
btn_forward.bind('<ButtonPress-1>', lambda event: setButtonMessage(0x03, 0x13, 0x01))
btn_forward.bind('<ButtonRelease-1>', lambda event: setButtonMessage(0, 0, 0))

btn_back = tk.Button(root, text="OK")
btn_back.bind('<ButtonPress-1>', lambda event: setButtonMessage(0x00, 0x13, 0x10))
btn_back.bind('<ButtonRelease-1>', lambda event: setButtonMessage(0, 0, 0))


btn_up.pack(pady=10)
btn_down.pack(pady=10)
btn_forward.pack(pady=10)
btn_back.pack(pady=10)
canvas = tk.Canvas(root, width=200, height=150)
canvas.pack()
# Create a CAN bus object
bus = can.interface.Bus(channel='com9', bustype='seeedstudio', bitrate=500000)

# Create threads for sending and receiving messages
send_thread_20ms = threading.Thread(target=send_messages_20ms, args=(bus,))
send_thread_100ms = threading.Thread(target=send_messages_100ms, args=(bus,))
testing_5s = threading.Thread(target=testing_5s_function, args=(bus,))
receive_thread = threading.Thread(target=receive_messages, args=(bus,))
game_socket_thread = threading.Thread(target=connect_to_game_socket)

# Start the sending, receiving, and game socket threads
send_thread_20ms.start()
send_thread_100ms.start()
testing_5s.start()
receive_thread.start()
game_socket_thread.start()
root.mainloop()

# Wait for the threads to finish
send_thread_20ms.join()
send_thread_100ms.join()
testing_5s.join()
receive_thread.join()
game_socket_thread.join()

# Shutdown the CAN bus
bus.shutdown()
