"""
    Filename: camera_yolo_classification.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo
    
    Description: 
        Displays an image stream from the camera of a single simulated drone in Airsim (using the Airsim API) and returns the classification of the image using a YOLO classification model.                                                                                                                              
"""

import cv2 as cv
from ultralytics import YOLO
import airsim


def main():

    client = airsim.MultirotorClient(ip="172.24.112.1")
    client.confirmConnection()
    client.enableApiControl(True)

    model = YOLO("/home/cameron/yolo_v11_custom/yolo_dataset/trained_models/best.pt")
    
    #results = []

    while True:
        
        frame = client.simGetImage("0", airsim.ImageType.Scene)

        nparr = airsim.string_to_uint8_array(frame)
        img = cv.imdecode(nparr, cv.IMREAD_COLOR)

        results = model.predict(source = img)
        
        annotated_frame = results[0].plot()
        cv.imshow('Classification Predictions',annotated_frame)
        
        #print(results[0])

        #with open("results.txt", "w") as file:
        #    file.writelines(str(results))

        # Press 'q' from the video window to quit.
        if cv.waitKey(1) == ord('q'):
            #with open('output.png', 'wb') as image_file:
            #    image_file.write(nparr)
            break
    
    cv.destroyAllWindows()

if __name__ == "__main__":                                                                             
     main()

