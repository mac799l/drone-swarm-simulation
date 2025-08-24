"""
    Filename: multi_uav_script.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo

    Description: 
        Defines control scripts for four drones and then using multithreading to accomplish simultaneous operation.
        
"""

from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
from dronekit import connect
import time
import threading
from droneclass_dk import drone


def connectCopter(connection):
    
    if not connection:
        connection = "/dev/serial0"
        print("No connection argument! Defaulting to /dev/serial0.")

    print("Connecting to: ",connection)

    vehicle = connect(connection, wait_ready=True)
    return vehicle


# Define the movement commands for the first drone.
def drone_control_0(copter):

    AIRSPEED = 8
    GROUNDSPEED = 8

    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    copter.takeoff(20)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")

    # Move Northwest for 8 seconds.    
    copter.send_global_ned_velocity(8,-4,0,8)
    time.sleep(1)
    # Move North for 4 seconds.
    copter.send_global_ned_velocity(8,0,0,4)
    time.sleep(1)
    
    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()


# Define the movement commands for the second drone.
def drone_control_1(copter):
    
    AIRSPEED = 8
    GROUNDSPEED = 8

    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    copter.takeoff(20)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")
    
    # Move Northeast for 8 seconds.
    copter.send_global_ned_velocity(8,4,0,8)
    time.sleep(1)
    # Move North for 4 seconds.
    copter.send_global_ned_velocity(8,0,0,4)
    time.sleep(1)
    
    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()


# Define the movement commands for the third drone.
def drone_control_2(copter):
    AIRSPEED = 8
    GROUNDSPEED = 8

    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    copter.takeoff(20)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")
    
    # Move Southwest for 8 seconds.
    copter.send_global_ned_velocity(-8,-4,0,8)
    time.sleep(1)
    # Move South for 4 seconds.
    copter.send_global_ned_velocity(-8,0,0,4)
    time.sleep(1)
    
    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()
 

# Define the movement commands for the fourth drone.
def drone_control_3(copter):

    AIRSPEED = 8
    GROUNDSPEED = 8

    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    copter.takeoff(20)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")

    # Move Southeast for 8 seconds.    
    copter.send_global_ned_velocity(-8,4,0,8)
    time.sleep(1)
    # Move South for 4 seconds.
    copter.send_global_ned_velocity(-8,0,0,4)
    time.sleep(1)

    
    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()


def main():

    vehicles = []
    copters = []
    with open("connections.txt","r") as file:
        for arg in file:
            print("Connecting to: ",arg.strip())
            connect = arg.strip()
            vehicle = connectCopter(connection=connect)
            copter = drone(vehicle)
            copters.append(copter)
            vehicles.append(vehicle)

    drone_controls = [drone_control_0,drone_control_1,drone_control_2,drone_control_3]
    threads = []
    for i, copter in enumerate(copters):
        thread = threading.Thread(target=drone_controls[i], args=(copter,))
        threads.append(thread)

    print("Starting drones.")
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
    
    print("Closing vehicle connections.")
    for vehicle in vehicles:
        vehicle.close()

    print("Script complete.")


if __name__ == "__main__":
    main()
