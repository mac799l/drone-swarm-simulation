"""
    Filename: single_uav_classification.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo

    Description:
    This script commands a connected drone to follow a preset path defined in the control function.
    It also performs classification using a Gstreamer udp video source from the Ardupilot Gazebo Gstreamer plugin using YOLO and Opencv.

    NOTE: the script is currently designed to perform YOLO classification using a YOLO model trained on the MEDIC disaster dataset.
    Minor modifications would be needed to perform other tasks.

    Arguments:
    --connect PROTOCOL:IP:PORT (provide the connection information, otherwise defaults to a serial connection).
"""

from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
from dronekit import connect
from droneclass_dk import drone
import time
import argparse
import cv2 as cv
from ultralytics import YOLO
import threading
from enum import Enum
import airsim
import numpy as np

# Detected classes for use by a YOLO model trained on the MEDIC dataset.
class Disaster(Enum):
    EARTHQUAKE = 0
    FIRE = 1
    FLOOD = 2
    HURRICANE = 3
    LANDSLIDE = 4
    NOT_DISASTER = 5
    OTHER_DISASTER = 6


# Connect to the drone.
def connectCopter():

    connection = argParser()
    # Default to a physical connection (i.e. RaspberryPi serial connection).
    if not connection:
        connection = "/dev/serial0"
        print("No connection argument! Attempting to connect over serial.")

    print(connection)

    vehicle = connect(connection, wait_ready=True)
    return vehicle

# Connected to camera stream.
def connectCamera():

    # Print information to verify if Gstreamer is enabled.
    #print(cv.getBuildInformation())

    client = airsim.MultirotorClient(ip="172.24.112.1")
    client.confirmConnection()
    client.enableApiControl(True)

    return client


# Perform classification on the camera stream.
def classificationYOLO(client, copter):

    DETECTION_THRESHOLD = 0.5
    model = YOLO("/home/cameron/yolo_v11_custom/yolo_dataset/trained_models/best.pt")
    frame_data = []
    frame_data.append([0,"NOT_DISASTER", 0, [0,0,0]])

    while True:

        frame = client.simGetImage("0", airsim.ImageType.Scene)
        nparr = np.frombuffer(frame, np.uint8)
        img = cv.imdecode(nparr, cv.IMREAD_COLOR)

        results = model.predict(source = img, verbose = True)
        annotated_frame = results[0].plot()
        cv.imshow('Camera feed',annotated_frame)

        probabilites = results[0].probs
        top_class = probabilites.top1
        confidence = probabilites.top1conf
        enum_name = Disaster(top_class).name
        location = copter.getLocationGlobal()

        if enum_name != "NOT_DISASTER" and confidence > DETECTION_THRESHOLD:
            print("Detected class:", enum_name ,"-- Probability:",'{0:.2f}'.format(confidence.item()), " -- GPS:", location)
            if enum_name != frame_data[-1][1]:
                frame_data.append([frame, enum_name, confidence, location])
            elif frame_data[-1][2] < confidence:
                frame_data.pop()
                frame_data.append([frame, enum_name, confidence, location])

        # Press 'q' from the camera window to quit.
        if cv.waitKey(1) == ord('q'):
            break

    cv.destroyAllWindows()

    return


def droneControl(copter):

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(50)

    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 0, velocity_z = 0, duration = 15)
    time.sleep(5)

    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()

    return

def argParser():

    parser = argparse.ArgumentParser(description='commands')
    parser.add_argument('--connect')
    args = parser.parse_args()
    connection = args.connect
    
    return connection

def main():

    copter_connection = connectCopter()
    client = connectCamera()

    copter = drone(copter_connection)

    drone_operations = [droneControl,classificationYOLO]
    arguments = [[copter,], [client, copter]]
    threads = []

    for i, arg in enumerate(arguments):
        thread = threading.Thread(target=drone_operations[i], args=arg)
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    time.sleep(1)
    print("Finished script. Closing connections.")

    # Close connections.
    copter_connection.close()


if __name__ == "__main__":
    main()
