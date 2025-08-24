"""
    Filename: single_uav_script_pml.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo

    Description: 
    This script commands a connected drone to follow a preset path defined in the control function using Dronekit. 
    
    Arguments: 
    --connect PROTOCOL:IP:PORT (provide the connection information, otherwise defaults to a serial connection).
"""

from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
from dronekit import connect
import time
import argparse
from droneclass_dk import drone as drone


def connectCopter():
    parser = argparse.ArgumentParser(description='commands')
    parser.add_argument('--connect')
    args = parser.parse_args()
    connection = args.connect

    # Default to a physical connection (i.e. RaspberryPi serial).    
    if not connection:
        connection = "/dev/serial0"
        print("No connection argument!")

    print("Connecting to: ",connection)

    vehicle = connect(connection, wait_ready=True)
    return vehicle


def main():

    AIRSPEED = 8
    GROUNDSPEED = 8

    vehicle = connectCopter()

    copter = drone(vehicle)
    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    time.sleep(1)
    copter.takeoff(5)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")
    
    # Move North for 10 seconds.
    copter.send_global_ned_velocity(8,0,0,10)
    
    # Move South for 5 seconds.
    copter.send_global_ned_velocity(-8,0,0,5)
    
    # Move East for 10 seconds.
    copter.send_global_ned_velocity(0,8,0,10)
    
    # Move West for 5 seconds.
    copter.send_global_ned_velocity(0,-8,0,5)
   
    copter.go_to(copter.getHome())
    
    copter.land()
    time.sleep(1)
    
    print("Finished script. Closing connections.")
    vehicle.close()

if __name__ == "__main__":
    main()
