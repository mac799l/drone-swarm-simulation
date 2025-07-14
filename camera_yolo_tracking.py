"""
    Filename: camera_yolo_tracking.py
    Author: Cameron Lira
    Date: 2025-07-14
    Version: 1.0
    Project: Drone Swarm Control Using SITL and Gazebo
    Description: This script displays a video stream from the camera of a simulated drone in Gazebo with the bounding boxes computed by a YOLO object detection model.                                                                                                                              
"""

import cv2 as cv
import time
from ultralytics import YOLO
import string


def main():

    # Print information to verify if Gstreamer is enabled.
    #print(cv.getBuildInformation())

    pipeline = "udpsrc port=5600 caps=application/x-rtp,media=video,encoding-name=H264 ! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
    camera_stream = cv.VideoCapture(pipeline,cv.CAP_GSTREAMER)

    if not camera_stream.isOpened():
        print("Error reading video.")
        exit(1)

    model = YOLO("yolo11x.pt")

    while True:
        
        ret, frame = camera_stream.read()
        results = model.track(source = frame, persist=True)
        
        annotated_frame = results[0].plot()
        cv.imshow('Display window',annotated_frame)
        
        print(results[0])

        # Press 'q' from the video window to quit.
        if cv.waitKey(1) == ord('q'):
            break

    camera.release()
    cv.destroyAllWindows()



if __name__ == "__main__":                                                                             
     main()

