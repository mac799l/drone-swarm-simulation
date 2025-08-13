"""
    Filename: droneclass_dk.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo

    Description: 
        Defines the drone control class (using Dronekit) for use in other scripts.
"""

from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
from dronekit import VehicleMode, LocationGlobalRelative
import time
from pymavlink import mavutil


class drone():
    
    def __init__(self, vehicle):
        self.vehicle = vehicle

    airspeed = 0
    groundspeed = 0
    home = []
    
    # Arm the copter in preparation for flight.
    def arm(self):
        if self.vehicle.armed == True:
            print("Vehicle armed!")
            return
        self.vehicle.armed = True
        while not self.vehicle.armed:
            print("Attempting to arm vehicle.")
            time.sleep(1)
        print("Vehicle armed.")
        return
    
    # Print basic drone status information.
    def printInfo(self):
        PRINTALL = False 
        if PRINTALL:
            print("\nPrint all parameters (iterate `vehicle.parameters`):")
            for key, value in self.vehicle.parameters.iteritems():
                print(" Key: ", key,"Value: ", value)
        else:
            print("Vehicle information:")
            print("GPS: ", self.vehicle.gps_0)
            print("Global Location:", self.vehicle.location.global_frame)
            print("Global Location (relative altitude):", self.vehicle.location.global_relative_frame)
            print("Local Location:", self.vehicle.location.local_frame)    #NED
            print("Battery: ", self.vehicle.battery)
            print("Last heartbeat: ", self.vehicle.last_heartbeat)
            print("Armed: ", self.vehicle.armed)
            print("Armable: ", self.vehicle.is_armable)
            print("Status: ", self.vehicle.system_status.state)
            print("Mode: ", self.vehicle.mode.name)

        return
    
    
    # Set drone flight mode.
    def setMode(self, mode):
        MODES = ["LAND","AUTO", "GUIDED", "STABILIZE", "LOITER", "RTL", "MANUAL"]

        if self.vehicle.mode == mode:
            print("Mode already set to \"",mode,"\".")
            return
        if mode not in MODES:
            print("Invalid mode selection!")
            return

        self.vehicle.mode = VehicleMode(mode) 
        while not self.vehicle.mode.name == mode:
            print("Attempting to set mode to \"",mode,"\".")
            print("Current mode: ",self.vehicle.mode)
            time.sleep(1)
        print("Mode set to \"",mode,"\".")
        return


    # Return altitude.
    def getAltGlobal(self):
        return self.vehicle.location.global_relative_frame.alt


    # Return GPS location (lat, lon, alt).
    def getLocationGlobal(self):
        curr_loc = [self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon, self.vehicle.location.global_relative_frame.alt]
        return curr_loc


    # Takeoff from the ground to selected target height in meters.
    def takeoff(self, target):
        TOLERANCE = 0.9
        curr_alt = self.getAltGlobal()
        if (curr_alt > 0.3):
            print("Vehicle already off the ground! Moving to target altitude: ", target)
            curr_loc = self.getLocationGlobal()
            curr_loc[2] = target
            self.go_to(curr_loc)
            return
            
        if self.vehicle.mode.name != "GUIDED":
            self.setMode("GUIDED")
        
        self.arm()
        print("Taking off to a height of ", target, " meters!")
        self.vehicle.simple_takeoff(target)

        while True:
            alt = self.getAltGlobal()
            print("Current altitude: ", alt)
            if alt >= target * TOLERANCE:
                print("Target altitude reached!")
                break
            time.sleep(1)
        return


    # Land the drone.
    def land(self):
        self.setMode("LAND")
        return


    # Set home location.
    def setHome(self): 
        self.home = self.getLocationGlobal()
        print("Home in setHome",self.home)
        return


    # Return home location.
    def getHome(self):
        print("Home in getHome: ",self.home)
        return self.home


    # Set target speed of the drone.
    def setSpeed(self, AIRSPEED, GROUNDSPEED):
        self.airspeed = AIRSPEED
        self.groundspeed = GROUNDSPEED
        self.vehicle.airspeed = AIRSPEED
        self.vehicle.groundspeed = GROUNDSPEED
        return

    
    def send_body_ned_velocity(self, velocity_x, velocity_y, velocity_z, duration):
        """
        Move vehicle in direction based on specified velocity vectors.
        """
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,#MAV_FRAME_BODY_OFFSET_NED, # frame
            0b110111000111,#0b0000111111000111, # type_mask (only speeds enabled)
            0, 0, 0, # x, y, z positions (not used)
            velocity_x, velocity_y, velocity_z, # x, y, z velocity in m/s
            0, 0, 0, # x, y, z acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)

        # send command to vehicle on 1 Hz cycle
        for x in range(0,duration):
            self.vehicle.send_mavlink(msg)
            time.sleep(1)


    def send_global_ned_velocity(self, velocity_x, velocity_y, velocity_z, duration):
        """
        Move vehicle in direction based on specified velocity vectors, relative to frame.
        """
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_LOCAL_NED, # frame
            0b110111000111,#1b0000111111000111, # type_mask (only speeds enabled)
            0, 0, 0, # x, y, z positions (not used)
            velocity_x, velocity_y, velocity_z, # x, y, z velocity in m/s
            0, 0, 0, # x, y, z acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)

        # send command to vehicle on 1 Hz cycle
        for x in range(0,duration):
            self.vehicle.send_mavlink(msg)
            time.sleep(1)


    # Move drone to given location in the form (lat, lon, alt).
    def go_to(self, target):
        MIN_TOLERANCE = 0.9999995
        MAX_TOLERANCE = 1.0000005
        MINHEIGHT = 1
        self.setSpeed(self.airspeed, self.groundspeed)
       
        print(target)
        if target[2] > MINHEIGHT:
            location = LocationGlobalRelative(target[0], target[1], target[2])
        else:
            target[2] = MINHEIGHT
            location = LocationGlobalRelative(target[0], target[1], MINHEIGHT)
        
        self.vehicle.simple_goto(location)
        curr_loc = self.getLocationGlobal()
        
        at_target = False 
        while not at_target:
            curr_loc = self.getLocationGlobal()
            print("Moving to location. Current: ",curr_loc)
            at_target = True 
            for i in range(2):
                curr_position = abs(curr_loc[i])
                curr_target = abs(target[i])
                if (curr_position < curr_target * MIN_TOLERANCE or curr_position > curr_target * MAX_TOLERANCE):
                    at_target = False
            time.sleep(1)
        
        time.sleep(3)
        print("Target reached!")
        return