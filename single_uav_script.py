#from asyncio.windows_events import NULL
from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
#import dronekit
from dronekit import connect, VehicleMode, LocationGlobalRelative, APIException
import time
import argparse
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

        ''' PRINT ALL PARAMETERS OPTION
        print "\nPrint all parameters (iterate `vehicle.parameters`):"
        for key, value in vehicle.parameters.iteritems():
        print " Key:%s Value:%s" % (key,value)
        '''
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
        #self.home = [self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon, self.vehicle.location.global_relative_frame.alt]
        self.home = self.getLocationGlobal()
        print("Home in setHome",self.home)
        #self.vehicle.home_location = self.home
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

    
    def send_local_ned_velocity(self, velocity_x, velocity_y, velocity_z, duration):
        """
        Move vehicle in direction based on specified velocity vectors.
        """
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED, # frame
            0b0000111111000111, # type_mask (only speeds enabled)
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
        Move vehicle in direction based on specified velocity vectors.
        """
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_LOCAL_NED, # frame
            0b0000111111000111, # type_mask (only speeds enabled)
            0, 0, 0, # x, y, z positions (not used)
            velocity_x, velocity_y, velocity_z, # x, y, z velocity in m/s
            0, 0, 0, # x, y, z acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)


        # send command to vehicle on 1 Hz cycle
        for x in range(0,duration):
            self.vehicle.send_mavlink(msg)
            time.sleep(1)

    #def go_to(self, x, y, z):
    #    a_location = LocationGlobalRelative(-34.364114, 149.166022, 30)

    # Move drone to given location in the form (lat, lon, alt).
    def go_to(self, target):
        TOLERANCE = 0.9999995
        MTOL = 1.0000005
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
                curr = abs(curr_loc[i])
                curr_t = abs(target[i])
                if (curr < curr_t * TOLERANCE or curr > curr_t * MTOL):
                    at_target = False
            time.sleep(1)
        
        time.sleep(3)
        print("Target reached!")
        return


def connectCopter():
    parser = argparse.ArgumentParser(description='commands')
    parser.add_argument('--connect')
    args = parser.parse_args()
    connection = args.connect
    
    if not connection:
        connection = "/dev/serial0"
        print("No connection argument!")

    print(connection)

    vehicle = connect(connection, wait_ready=True)#, baud=57600)
    #vehicle = connect('/dev/serial0', wait_ready=True, baud=57600)
    return vehicle

def connectCopterSITL():
    import dronekit_sitl
    sitl = dronekit_sitl.start_default()
    connection = sitl.connection_string()
    vehicle = connect(connection, wait_ready=True)
    print("Connected to drone!")
    return vehicle, sitl

def main():
    #Enable/disable SITL vehicle creation.
    SITL = False 
    AIRSPEED = 8
    GROUNDSPEED = 8

    #if SITL:
        #vehicle, sitl = connectCopterSITL();
    #else:
        #vehicle = connectCopter()

    #copter = drone(vehicle)
    if SITL:
        import dronekit_sitl
        sitl = dronekit_sitl.start_default()
        connection = sitl.connection_string()
        vehicle = connect(connection, wait_ready=True)
        print("Connected to drone!")
    else:
        vehicle = connectCopter()

    copter = drone(vehicle)
    copter.setHome()
    
    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)
    
    time.sleep(1)
    copter.takeoff(5)
    
    time.sleep(1)
    print("Altitude: ",copter.getAltGlobal(), "meters.")
    
    copter.send_global_ned_velocity(8,4,0,8)
    #time.sleep(1)
    copter.send_global_ned_velocity(8,-5,0,8)
    #time.sleep(1)
    #copter.send_global_ned_velocity(-8,0,0,1)
    #time.sleep(1)
    #copter.send_global_ned_velocity(0,-8,0,10)
    #time.sleep(1)
    
    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()
    #copter.setMode("RTL")
    time.sleep(1)
    print("Finished script. Closing connections.")
    #Close connections.
    vehicle.close()
    if SITL:
        sitl.stop()


if __name__ == "__main__":
    main()
