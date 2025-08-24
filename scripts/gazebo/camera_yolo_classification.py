"""
    Filename: camera_yolo_classification.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo
    
    Description: 
        Displays a video stream from the camera of a simulated drone in Gazebo and returns the classification of the image using a YOLO classification model.                                                                                                                              
"""

import cv2 as cv
import time
from ultralytics import YOLO
import string


def main():

    # Print information to verify if Gstreamer is enabled.
    #print(cv.getBuildInformation())

    PATH_TO_YOLO_MODEL = "trained_models/best.pt"

    pipeline = "udpsrc port=5600 caps=application/x-rtp,media=video,encoding-name=H264 ! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
    camera_stream = cv.VideoCapture(pipeline,cv.CAP_GSTREAMER)

    if not camera_stream.isOpened():
        print("Error reading video.")
        exit(1)

    model = YOLO(PATH_TO_YOLO_MODEL)
    
    results = []

    while True:
        
        ret, frame = camera_stream.read()
        results = model.predict(source = frame)
        
        annotated_frame = results[0].plot()
        cv.imshow('Display window',annotated_frame)
        
        #print(results[0])

        with open("results.txt", "w") as file:
            file.writelines(str(results))

        # Press 'q' from the video window to quit.
        if cv.waitKey(1) == ord('q'):
            break
        
    camera_stream.release()
    cv.destroyAllWindows()

if __name__ == "__main__":                                                                             
     main()

