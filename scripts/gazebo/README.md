`camera_stream.py`: Displays a video stream from the camera of a simulated drone in Gazebo using Gstreamer and Opencv.

`camera_yolo_classification.py`: Displays a video stream from the camera of a single simulated drone in Gazebo and returns the predicted classes of the image using a YOLO classification model.                                                                         

`camera_yolo_tracking.py`: Displays a video stream from the camera of a simulated drone in Gazebo with the bounding boxes computed by a YOLO object detection model.

`droneclass_dk.py`: Defines the drone control class (using Dronekit) for use in other scripts.

`multi_uav_script.py`: Defines control scripts for four drones and then using multithreading to accomplish simultaneous operation.

`single_uav_classification.py`: Commands a connected drone to follow a preset path defined in the control function. It also performs classification using a Gstreamer udp video source from the Ardupilot Gazebo Gstreamer plugin using YOLO and Opencv.

>NOTE: it is currently designed to perform YOLO classification using a YOLO model trained on the MEDIC disaster dataset. Minor modifications would be needed to perform other tasks.

`single_uav_script.py`: Commands a connected drone to follow a preset path defined in the control function.