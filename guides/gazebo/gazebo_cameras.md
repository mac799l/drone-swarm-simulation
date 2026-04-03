## Gazebo Drone Cameras

Thankfully, the drone models already include a Gazebo camera and the camera feeds can be accessed directly from Gazebo by opening up the ```Image Display``` tab (click the three dots on the top right of the window and find the ```Image Display``` option). If you have multiple drones in the environment, you can view each camera by switching between them in the drop down menu of the Image Display tab.

<p align="center">
  <img src="https://github.com/user-attachments/assets/ff43683f-ed3f-4696-b713-ef37b3ed4e5a" width="720" height="480">
</p>

However, if we want to do machine vision tasks, we will want to be able to access the camera stream from our own scripts. Doing this with a single drone requires no additional configuration and you can follow the next section about enabling the camera stream. However, if we are using multiple drones and wish to access their cameras, we will need to ensure the cameras are streaming to different ports first and the process I used is somewhat involved.

### Using Multiple Camera Streams

The first step is to navigate to your models folder at ```~/gz_ws/src/ardupilot_gazebo/models``` and note that the model.sdf file in each of your ```iris_with_gimbal_x``` drone folders has the following lines:

```
<include>
 <uri>model://gimbal_small_3d</uri>
 <name>gimbal</name>
 <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
```

This is the part of the sdf file that includes the gimbal model. Furthermore, the gimbal's model.sdf file in the ```gimbal_small_3d``` folder includes the following lines:

```
<plugin name="GstCameraPlugin" 
  filename="GstCameraPlugin">
  <udp_host>127.0.0.1</udp_host>
  <udp_port>5600</udp_port>
  <use_basic_pipeline>true</use_basic_pipeline>
  <use_cuda>false</use_cuda>
</plugin>
```

The ```GstCameraPlugin``` is what streams the camera feed using [Gstreamer](https://gstreamer.freedesktop.org/). Note the ```<udp_port>5600</udp_port>``` option. Since we need a unique port for each camera (or different IPs), we will need each drone to reference a unique gimbal (since the camera plugin is attached to the gimbal, which is attached to the drone). To do this, create copies of the ```gimbal_small_3d``` folder like we did with the ```iris_with_gimbal``` folders until you have ```gimbal_small_3d_1```, ```gimbal_small_3d_2```, etc. for each drone you plan to use. You don't have to change the model name inside each gimbal folder.

Now, in each of your ```iris_with_gimbal_x``` folders, include the correct gimbal to match the folder name of the respective drone:

In ```iris_with_gimbal_1```:
```
<include>
  <uri>model://gimbal_small_3d_1</uri>                                                                                                                                                                                              
  <name>gimbal</name>
  <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
```

In ```iris_with_gimbal_2```:
```
<include>
  <uri>model://gimbal_small_3d_2</uri>                                                                                                                                                                                              
  <name>gimbal_2</name>
  <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
```

and so on...


Now, for each gimbal folder edit the camera plugin settings by incrementing the udp port like so:


In ```gimbal_small_3d_1``` (port value stays the same):
```
214         <plugin name="GstCameraPlugin"
215             filename="GstCameraPlugin">
216           <udp_host>127.0.0.1</udp_host>
217           <udp_port>5600</udp_port>
218           <use_basic_pipeline>true</use_basic_pipeline>
219           <use_cuda>false</use_cuda>
220         </plugin>
```


In ```gimbal_small_3d_2``` (increment the port number):
```
214         <plugin name="GstCameraPlugin"
215             filename="GstCameraPlugin">
216           <udp_host>127.0.0.1</udp_host>
217           <udp_port>5700</udp_port>
218           <use_basic_pipeline>true</use_basic_pipeline>
219           <use_cuda>false</use_cuda>
220         </plugin>
```

and so on...


> If you need to send the camera feed to different ip addresses, you can edit the ```<udp_host>127.0.0.1</udp_host>``` parameter to the IP of the device you want to access the stream. Now the cameras should be set up.

#### Testing the Cameras

> This section is an expansion of the official Ardupilot Gazebo Plugin [README's](https://github.com/ArduPilot/ardupilot_gazebo) section on accessing the cameras.

A simple way to test the camera streams is to use Gstreamer directly. In order to do this, you can install Gstreamer by following the instructions [here](https://gstreamer.freedesktop.org/documentation/installing/on-linux.html?gi-language=c). Once you have installed gstreamer, you need to enable streaming for each camera you want to use. This can be done be referencing the Gazebo camera topic (there will be one for each camera included in the world file).

After opening Gazebo, use another terminal to list the Gazebo topics:

```sh
gz topic -l
```

You should see an entry toward the bottom like this for each drone camera in the scene:

```
/world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming
```

This the Gazebo topic that starts the camera stream. To enable it:

```sh
gz topic -t /world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p "data: 1"
```

Replace the ```/world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming``` topic with how it is printed from your Gazebo topic list. Do this for each ```enable_streaming``` topic.


Finally, we can test the camera streams. To view a stream, run the following command with the correct ```udpsrc port```:

```sh
gst-launch-1.0 -v udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
```

You should get a camera feed that looks like this:

<p align="center">
  <img src="https://github.com/user-attachments/assets/757f4614-3d14-476a-8cf0-15e4316e7097" width="771" height="638">
</p>

#### Accessing the Camera within Python

In order to access the camera stream using Python, we will be using the OpenCV library and Gstreamer. In order for this to work, OpenCV needs to built with Gstreamer. A guide to accomplish this can be found [here](https://galaktyk.medium.com/how-to-build-opencv-with-gstreamer-b11668fa09c). For simplicity, you may want to create a new Python virtual environment for your machine vision tasks and install OpenCV with Gstreamer into that environment. For example, I created a virtual environment for using YOLO models and installed OpenCV into that environment, that way I had an environment for running my SITL simulations and an environment for my machine vision processing.


Once you have installed OpenCV and verified that it works with Gstreamer, you can use the ```image_stream.py``` python file to access one of those streams like so:

```sh
python image_stream.py
```

This will open the same window as when we ran Gstreamer directly, but now you are streaming the video through Python and can access the stream for processing. Here is an example of running a YOLO object detection model on the data stream:

<p align="center">
  <img src="https://github.com/user-attachments/assets/e6a0390b-802c-48e9-bba3-173000657693" width="770" height="638">
</p>