import ac
import acsys
import socket
import struct
import time

# Set up the UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('127.0.0.1', 4567)


# Function to fetch data from Assetto Corsa
def fetch_ac_data():
    # Fetching data from Assetto Corsa
    rpm = ac.getCarState(0, acsys.CS.RPM)
    speed = ac.getCarState(0, acsys.CS.SpeedMS)
    coolant_temp = 60
    oil_temp = 60
    fuel = 50
    gear = ac.getCarState(0, acsys.CS.Gear)-1
    boost = ac.getCarState(0, acsys.CS.TurboBoost)

    # Example additional data
    gearSelector = 'D'  # Placeholder for actual gear selector state
    shiftlight = False  # Placeholder for actual shiftlight state
    highbeam = False  # Placeholder for actual highbeam state
    handbrake = False  # Placeholder for actual handbrake state
    tc_active = False  # Placeholder for actual TC active state
    tc_off = False  # Placeholder for actual TC off state
    left_directional = False  # Placeholder for actual left directional state
    right_directional = False  # Placeholder for actual right directional state
    lowoilpressure = False  # Placeholder for actual low oil pressure state
    battery = False  # Placeholder for actual battery state
    abs_active = False  # Placeholder for actual ABS active state
    abs_fault = False  # Placeholder for actual ABS fault state
    ignition = True  # Placeholder for actual ignition state
    lowpressure = False  # Placeholder for actual low pressure state
    check_engine = False  # Placeholder for actual check engine state
    foglight = False  # Placeholder for actual foglight state
    lowbeam = False  # Placeholder for actual lowbeam state
    cruise_control_active = False  # Placeholder for actual cruise control active state

    packet = struct.pack('2c7f2I3f',
                         gearSelector.encode(), str(gear).encode(),
                         speed, rpm, boost, coolant_temp, fuel, 0, oil_temp,
                         (shiftlight << 0) | (highbeam << 1) | (handbrake << 2) | (tc_active << 4) | (tc_off << 5) | (left_directional << 6) | (right_directional << 7) | (lowoilpressure << 8) | (battery << 9) | (abs_active << 10) | (abs_fault << 11) | (ignition << 12) | (lowpressure << 13) | (check_engine << 14) | (foglight << 15) | (lowbeam << 16) | (cruise_control_active << 17), 0,
                         0.0, 0.0, 0.0)
    
    return packet

# Main loop to send data
def acMain(ac_version):
    return "BetterTelemetry"

def acUpdate(deltaT):
    packet = fetch_ac_data()
    sock.sendto(packet, server_address)

def acShutdown():
    ac.log("Shutting down")
