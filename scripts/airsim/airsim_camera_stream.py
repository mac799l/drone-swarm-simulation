"""
    Filename: airsim_camera_stream.py
    Author: Cameron Lira
    Updated: 2025-08-24
    Project: Drone Swarm Simulation

    Description: 
        Displays images from the camera of a simulated drone in Airsim using the Airsim API and Opencv.
"""

import airsim
import cv2 as cv
import numpy as np

AIRSIM_HOST_IP = "172.24.112.1"

# connect to the AirSim simulator
client = airsim.MultirotorClient(ip=AIRSIM_HOST_IP)
client.confirmConnection()
client.enableApiControl(True)

# Select the front camera.
CAMERA_SELECTION = "0"
DRONE_NAME_1 = "Copter"
DRONE_NAME_2 = "Copter2"

responses = client.simGetImage(CAMERA_SELECTION, airsim.ImageType.Scene, vehicle_name=DRONE_NAME_1)

responses2 = client.simGetImage(CAMERA_SELECTION, airsim.ImageType.Scene, vehicle_name=DRONE_NAME_2)

print('Retrieved images: %d', len(responses))

nparr = np.frombuffer(responses, np.uint8)
img_np = cv.imdecode(nparr, cv.IMREAD_COLOR)

nparr2 = np.frombuffer(responses2, np.uint8)
img_np2 = cv.imdecode(nparr2, cv.IMREAD_COLOR)

# Display an image from each drone.
cv.imshow('',img_np)
cv.waitKey(0)
cv.imshow('',img_np2)
cv.waitKey(0)