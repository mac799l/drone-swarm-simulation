# ready to run example: PythonClient/multirotor/hello_drone.py
import airsim
import time
import cv2 as cv
import numpy as np


# connect to the AirSim simulator
client = airsim.MultirotorClient(ip="172.24.112.1")
client.confirmConnection()
client.enableApiControl(True)
#client.armDisarm(True)

# Async methods returns Future. Call join() to wait for task to complete.
#client.takeoffAsync().join()
#client.moveToPositionAsync(-10, 10, -10, 5).join()

#state = client.getMultirotorState()



# take images
'''
responses = client.simGetImages([
    # png format
    airsim.ImageRequest(0, airsim.ImageType.Scene),
    # uncompressed RGB array bytes
    airsim.ImageRequest(1, airsim.ImageType.Scene, False, False),
    # floating point uncompressed image
    airsim.ImageRequest(1, airsim.ImageType.DepthPlanar, True)])
'''
#responses = client.simGetImage("0", airsim.ImageType.Scene)

#print('Retrieved images: %d', len(responses))

responses = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name="Copter")

responses2 = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name="Copter2")

print('Retrieved images: %d', len(responses))

nparr = np.frombuffer(responses, np.uint8)
img_np = cv.imdecode(nparr, cv.IMREAD_COLOR)

nparr2 = np.frombuffer(responses2, np.uint8)
img_np2 = cv.imdecode(nparr2, cv.IMREAD_COLOR)

cv.imshow('',img_np)
cv.waitKey(0)
cv.imshow('',img_np2)
cv.waitKey(0)
#response2 = client.simGetImages([airsim.ImageRequest("camera_name", airsim.ImageType.Scene, False, False)])
