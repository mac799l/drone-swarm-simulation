"""
    Filename: airsim_camera_stream.py
    Author: Cameron Lira
    Updated: 2026-02-24
    Project: Drone Swarm Simulation

    Description: 
        Streams images from a drone camera in Airsim using the Airsim API and OpenCV. Press 'q' to close the stream window.
"""

import airsim
import cv2 as cv
import numpy as np

AIRSIM_HOST_IP = "172.24.112.1"

# connect to the AirSim simulator
airsim_client = airsim.MultirotorClient(ip=AIRSIM_HOST_IP)
airsim_client.confirmConnection()
airsim_client.enableApiControl(True)

# Select the front camera.
CAMERA_SELECTION = "0"
DRONE_NAME = "Copter0"


while True:
    frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=DRONE_NAME)
    nparr = np.frombuffer(frame, np.uint8)
    img = cv.imdecode(nparr, cv.IMREAD_COLOR)
    cv.imshow('Camera feed',img)

    # Press 'q' from the camera window to stop classification.
    if cv.waitKey(1) == ord('q'):
        break