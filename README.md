# Drone Swarm Control Using SITL and Gazebo
Before testing scripts and commands in the field (with real, and expensive, drones), it is possible to test in virtual environments and simulated vehicles first. The end goal is to test scripts, code, and techniques in a safe and easily replicable environment - which are then usable in the real world with actual drones. To that end, this guide will follow the process of getting a simple virtual environement and drone setup working using Ardupilot SITL and Gazebo-Harmonic.
> Note: this guide specifically uses drone models, but other vehicle types can be set up in a similar way.

## Conceptual Plan
This guide aims to complete the following tasks:
* Simulate the drone controller of an arbitrary number of drones.
* Have these drones run in a 3D environment to afford better visualization and enable machine vision tasks.
* Be able to control the drones through various methods, including code.
* Generate techniques and scripts that are applicable to real drones.

To accomplish this, we will be using several layers of software simulation. Firstly, we will be using the Gazebo simulator to create the 3D environment that the drones will inhabit. Second, to simulate the drone controller (for both metrics gathering and commanding the drone) we will be using Ardupilot's SITL (software in the loop). Third, we will set up the Gazebo-SITL plugin that allows us to have these programs work together. Finally, we will be using DroneKit and Pymavlink (in progress) to create control scripts for single and multi-uav projects.

## Pre-requisites
* A reasonably capable computer (a dedicated GPU, and at least 8GB of ram)
* Ubuntu 22.04 or Windows with WSL2 (with Ubuntu installed)
> Note: other versions of Ubuntu may also work, but were not tested.

## Software
### Gazebo
Gazebo is a popular robotics simulator. It allows for the simulation of detailed vehicles, drones, and robots. These simulations include physics, sensors and cameras, and even the individual components and motors of your robot.

<img src="https://github.com/user-attachments/assets/fca8dfa0-4d5b-4d6a-8b07-68a609e6c8dc" width="640" height="360">

> Gazebo image [source](https://gazebosim.org/showcase)

### SITL
Ardupilot's SITL is a tool that allows us to simulate the inner workings of the drone itself. Sensor data such as GPS location, various status and safety checks, battery level, and more are simulated. Additionally, SITL allows us to use real-world methods (e.g. [Mavlink messages](https://mavlink.io/en/)) to control the drone using the simulated drone controller.

![sitl](https://github.com/user-attachments/assets/4887f7e6-70c2-4b34-8aac-bdccba13c87d)

> SITL image [source](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)
# Installation

This section assumes you have installed Ubuntu 22.04 (or an official [Ubuntu 22.04 flavor](https://ubuntu.com/desktop/flavors)) either natively or through Windows WSL2. If not, a guide can be found [here](https://ubuntu.com/tutorials/install-ubuntu-desktop#1-overview). The Windows WSL2 installation guide can be found [here](https://learn.microsoft.com/en-us/windows/wsl/install).

### #1 - Gazebo
> Note: this section closely follows the official guide, which can be found [here](https://gazebosim.org/docs/harmonic/install_ubuntu/).

First, open a terminal and ensure Ubuntu is up to date, then install needed packages:
```sh
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install curl lsb-release gnupg
```
Install Gazebo:
```sh
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update
sudo apt-get install gz-harmonic
```

Run Gazebo and use the default shapes.sdf environment:
```sh
gz sim -v4 -r shapes.sdf
```
> The ```-v4``` option prints debugging information to the terminal.

This command should open Gazebo with a window like this:

<img src="https://github.com/user-attachments/assets/8ef2dcf4-07ae-464d-af67-d88400c01d89" width="808" height="700">


> Note: if the window fails to open, check the debug information from the terminal you started Gazebo in. If it reads
> ```[GUI] [Dbg] [Gui.cc:343] GUI requesting list of world names. The server may be busy downloading resources. Please be patient.```
> Then the issue is with your firewall configuration. To correct the issue, run the following commands to allow Gazebo through the firewall:
> ```sh
> sudo ufw allow in proto udp to 224.0.0.0/4
> sudo ufw allow in proto udp from 224.0.0.0/4
> ```

Now you have a fully-functioning Gazebo installation. But more configuration work will be required to make it work with SITL and simulate drones.

### #2 - SITL
> Note: this section closely follows the official guide, which can be found [here](https://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html).

Now to install Ardupilot SITL which will simulate the drone controller. The first step is to ensure that git is installed:
```sh
sudo apt-get update
sudo apt-get install git
```
Now clone the SITL repository from git and go into that directory:
```sh
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
```
The next step is to run the setup script for SITL:
```sh
Tools/environment_install/install-prereqs-ubuntu.sh -y
```
This script will take some time to complete, but performs all of the necessary setup for us. After that is complete, __log out and log back in__ to finalize the process.

The next step is to build the vehicle. To do this, you will need to connect to the python virtual environment first:

```sh 
source ~/venv-ardupilot/bin/activate
```

Now that we are using the Python environment, we can finally run a SITL instance:
```sh
sim_vehicle.py -v ArduCopter --console --map -w
```
> Note: this will take some time on the first run. Also, the ```-w``` option is recommended on the first run of SITL as it sets the vehicle parameters to their defaults.
> Also, the ```-v``` option specifies the vehicle type. For this guide we will be using the ArduCopter vehicle, but others are possible depending on your needs.

Once that is completed, some information about the drone should come up in the terminal (as well as an additional console interface with connection information). The terminal that the ```sim_vehicle.py``` command was run in will start a Mavproxy instance. [Mavproxy](https://ardupilot.org/mavproxy/) is a ground control station that communicates with the simulated drone, but its use is not a focus of this guide. Pressing enter a few times should display ```<STABILIZE>```. SITL should now be working.


### #3 - Ardupilot Gazebo Plugin
> Note: this section closely follows the official guide, which can be found [here](https://ardupilot.org/dev/docs/sitl-with-gazebo.html).

Now we will install the Gazebo plugin that will let us simulate our drone in Gazebo. First, ensure dependencies are installed.
```sh
sudo apt update
sudo apt install libgz-sim8-dev rapidjson-dev
sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
```
> Note: this may or may not actually install anything, depending on which libraries were already installed on your system.

Create a folder in the home directory for the plugin and clone the Gazebo plugin repository into it:
```sh
cd ~
mkdir -p gz_ws/src && cd gz_ws/src
git clone https://github.com/ArduPilot/ardupilot_gazebo
```
Build the plugin:

```sh
export GZ_VERSION=harmonic
cd ardupilot_gazebo
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j4
```

Add environment variables to your .bashrc file so Gazebo can access the plugin:

```sh
echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/gz_ws/src/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}' >> ~/.bashrc
echo 'export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}' >> ~/.bashrc
```

Finally, run Gazebo again, but this time with a iris_runway.sdf world provided by the Ardupilot plugin:
```sh
gz sim -v4 -r iris_runway.sdf
```
> Note: if the ```gz sim -v4 -r iris_runway.sdf``` command does not work, a system restart may be needed.

This should open a Gazebo project with a single drone on a runway like this:

<img width="808" height="700" alt="Screenshot_20250714_103302" src="https://github.com/user-attachments/assets/5c9b4333-e755-4f72-8b3f-f2369da80833" />

Now the Gazebo Plugin should be working.

### #4 - Test the Environment

With the previous Gazebo window still open, and in a separate terminal, we will connect to the drone using a SITL instance. In a second terminal, do the following:
Set the venv-ardupilot virtual Python environment as the source.
```sh
source ~/venv-ardupilot/bin/activate
```

Now create the SITL instance in the second terminal:
```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console
```

As before, this should create an instance of Mavproxy in the terminal. This should automatically connect to the Gazebo environment. After it sets up, press ```Enter``` a few times and you should see ```<STABILIZE>``` pop up. 
> Note: if desired, you can right click the drone in Gazebo and select for the viewport camera to follow it.

Finally, once the drone is fully initialized (GPS initialization is typically the last step), you can use these Mavproxy commands (one at a time) to make the drone takeoff:
```sh
mode GUIDED
arm throttle
takeoff 15
```
> Learn more about Mavproxy [here](https://ardupilot.org/mavproxy/).

These commands should start your drone motors (arm) and make it ascend to 15 meters in the Gazebo window. If an error occurs (i.e. the drone is not armable, etc.), then wait a few moments and try again, the drone may still be initializing. Now the drone should be fully functional, though Mavproxy commands are not the preferred way to control the drone long term. More advanced drone control methods - and how to set up multiple drones - are detailed below.

## Python Virtual Environment Setup
Now to set up the Python virtual environment so we can run some code. To do this ensure you are connected to the venv-ardupilot virtual environment:
```sh
source ~/venv-ardupilot/bin/activate
```

Now, ensure the following packages are installed:

```sh
pip install pymavlink dronekit MAVProxy
```
# Configuration

Now that the environment is setup, we can expand into controlling multiple drones, writing scripts, and implementing machine vision.

## Single Drone
We have already tested a single drone using Mavproxy commands. However, this interface is limited for more advanced purposes, so we will be using Dronekit (Pymavlink to be added later). In order to test using the provided single drone script, some additional options need to be specified.

> Note: Dronekit is a handy library for learning to code drone behaviour, but it lacks support and maintenance so I recommend transitioning to Pymavlink long-term.

Run Gazebo same as before:
gz sim -v4 -r iris_runway.sdf

Run SITL, but add the ```--out``` option to specify a forwarding IP and port for our code to connect to:
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --out udp:127.0.0.1:14550

> Note: '''--map''' and '''--console'' can be added back if desired.

Now you can run the provided code as follows (while connected to the ardupilot virtual environment as source):
python single_uav_script.py --connect udp:127.0.0.1:14550

### DroneKit

The Dronekit code provided creates a drone class with various simple commands that can be called on the drone object. The default main function simply makes the drone fly Northeast, then Northwest, and finally returns to the home location of the drone (saved as the takeoff location) and lands.

## Multiple Drones
> Note: this section is a modified version of the guide found [here](https://github.com/monemati/multiuav-gazebo-simulation).

In order to run multiple drones in Gazebo, some additional modifications need to be made. Firstly, go to your Ardupilot plugin models folder:

```sh
cd gz_ws/src/ardupilot_gazebo/models/
```

Now, you should see several vehicle model folders. Copy the ```iris_with_gimbal``` model for as many drones as you wish to create. I recommend leaving the original folder unaltered and creating ```iris_with_gimbal_x``` folders for each drone to be simulated (i.e. '''iris_with_gimbal_1''' and '''iris_with_gimbal_2''' and so on).

> Note: I have also provided a models folder with four models for the drones, which can be copied to your models directory to save time.

```sh
cp iris_with_gimbal iris_with_gimbal_1
```

Now, within each new ```iris_with_gimbal_x``` folder, change the ```<model name="iris_with_gimbal">``` option to ```<model name="iris_with_gimbal_X">``` where '''X''' is the number of the drone matching the folder name. Also, note the section ```<plugin name="ArduPilotPlugin"```. It should look something like this:

```
<plugin name="ArduPilotPlugin"
  <!-- Port settings -->
  <fdm_addr>127.0.0.1</fdm_addr>
  <fdm_port_in>9002</fdm_port_in>
```
For each subsequent drone (but not the first one), we will need to change the ```<fdm_port_in>``` option to a value that is __+10__. That is: drone #1 will be ```9002```, drone #2 will be ```9012```, and so on. 

Next, we will need to modify the world (Gazebo environment) to add the new drones. To do this, go to the ```~/gz_ws/src/ardupilot_gazebo/worlds``` folder and create a backup of the world file:

```sh
cp iris_runway.sdf iris_runway.sdf.bak
```

Now, edit the ```iris_runway.sdf``` world to include the other drones. For each drone, ensure the following lines are present at the end of the file:

```
<include>
  <uri>model://iris_with_gimbal_X</uri>
  <pose degrees="true">-10 0 0.195 0 0 90</pose>
</include>
```

Where ```X``` is the drone you are adding (from the name of the model folders copied earlier). Also, be sure to alter the ```<pose degrees="">``` values to change the starting position of the drones (the first three parameters are the X, Y, and Z coordinates, while the last three are the rotation). For example, for four drones, it would look like this:

```
<include>
  <uri>model://iris_with_gimbal_1</uri>
  <pose degrees="true">-10 0 0.195 0 0 90</pose>
</include>
<include>
  <uri>model://iris_with_gimbal_2</uri>
  <pose degrees="true">0 0 0.195 0 0 90</pose>
</include>
<include>
  <uri>model://iris_with_gimbal_3</uri>
  <pose degrees="true">10 0 0.195 0 0 90</pose>
</include>
<include>
  <uri>model://iris_with_gimbal_4</uri>
  <pose degrees="true">20 0 0.195 0 0 90</pose>
</include>
```

## Running the Swarm Simulation.

### DroneKit
The multi-uav script uses the ```connections.txt``` to read the IP addresses and ports of each connection (currently configured for four drones). No additional changes need to be made to it, unless you have altered the ```--out``` parameters in the SITL terminals below. The script has each drone fly away from the starting position in a different direction and then return the GPS coordinate of its home and land, much like the single-uav script. However, the script also implements multithreading to make the operation of each drone happen simulataneously. Each drone is controlled by its respective '''drone_control''' function.

Now we can launch Gazebo with the new environment (recall that we didn't change the name):

```sh
gz sim -v4 -r iris_runway.sdf
```

> Note: if you get instability with the drones - random shaking, etc. - you can try starting the SITL instances before launching Gazebo.

To run the code, open a new terminal for each drone. Now, with the Python virtual environment set as the source in each window, create the SITL instance and connect them to Gazebo:

In terminal #1:
```
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0 --out udp:127.0.0.1:14550
```
In terminal #2:
```
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I1 --out udp:127.0.0.1:14560
```
In terminal #3:
```
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I2 --out udp:127.0.0.1:14570
```
In terminal #4:
```
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I3 --out udp:127.0.0.1:14580
```

Now, in another terminal, go to the directory with the ```multi_uav_script.py``` and the ```connection.txt``` files and run the following command:

```sh
python multi_uav_script.py
```
> Remember to have the ```venv_ardupilot``` virtual environment set as the source.

Now the drones should takeoff, go in different directions and then return to the starting position. It is possible to create all the SITL instances from a single sim_vehicle.py command using '''--count''' command, but it caused issues with my multi-uav script, so I currently recommend using seperate terminals if you use my script.

## Gazebo Drone Cameras

Thankfully, the drone models already include a Gazebo camera and the camera feeds can be accessed directly from Gazebo by opening up the '''Image Display''' tab (click the three dots on the top right of the window and find the '''Image Display''' option). If you have multiple drones in the environment, you can view each camera by switching between them in the drop down menu of the Image Display tab.

<img width="720" height="480" alt="Screenshot_20250714_131243" src="https://github.com/user-attachments/assets/ff43683f-ed3f-4696-b713-ef37b3ed4e5a" />

However, if we want to do machine vision tasks, we will want to be able to access the camera stream from our own scripts. Doing this with a single drone requires no additional configuration and you can follow the next section about enabling the camera stream. However, if we are using multiple drones and wish to access their cameras, we will need to ensure the cameras are streaming to different ports first and the process I used is somewhat involved.

### Using Multiple Camera Streams

The first step is to navigate to your models folder at '''~/gz_ws/src/ardupilot_gazebo/models''' and note that the model.sdf file in each of your '''iris_with_gimbal_x''' drone folders has the following lines:

'''
<include>
 <uri>model://gimbal_small_3d</uri>
 <name>gimbal</name>
 <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
'''

This is the part of the sdf file that includes the gimbal model. Furthermore, the gimbal's model.sdf file in the '''gimbal_small_3d''' folder includes the following lines:

'''
<plugin name="GstCameraPlugin" 
  filename="GstCameraPlugin">
  <udp_host>127.0.0.1</udp_host>
  <udp_port>5600</udp_port>
  <use_basic_pipeline>true</use_basic_pipeline>
  <use_cuda>false</use_cuda>
</plugin>

'''

The '''GstCameraPlugin''' is what streams the camera feed using [Gstreamer](https://gstreamer.freedesktop.org/). Note the '''<udp_port>5600</udp_port>''' option. Since we need a unique port for each camera (or different IPs), we will need each drone to reference a unique gimbal (since the camera plugin is attached to the gimbal, which is attached to the drone). To do this, create copies of the '''gimbal_small_3d''' folder like we did with the '''iris_with_gimbal''' folders until you have '''gimbal_small_3d_1''', '''gimbal_small_3d_2''', etc. for each drone you plan to use. You don't have to change the model name inside each gimbal folder.

Now, in each of your '''iris_with_gimbal_x''' folders, include the correct gimbal to match the folder name of the respective drone:

In iris_with_gimbal_1:
'''
<include>
  <uri>model://gimbal_small_3d_1</uri>                                                                                                                                                                                              
  <name>gimbal</name>
  <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
'''

In iris_with_gimbal_2:
'''
<include>
  <uri>model://gimbal_small_3d_2</uri>                                                                                                                                                                                              
  <name>gimbal_2</name>
  <pose degrees="true">0 -0.01 -0.124923 90 0 90</pose>
</include>
'''

and so on...


Now, for each gimbal folder edit the camera plugin settings by incrementing the udp port like so:


In gimbal_small_3d_1 (stays the same):
'''
214         <plugin name="GstCameraPlugin"
215             filename="GstCameraPlugin">
216           <udp_host>127.0.0.1</udp_host>
217           <udp_port>5600</udp_port>
218           <use_basic_pipeline>true</use_basic_pipeline>
219           <use_cuda>false</use_cuda>
220         </plugin>
'''


In gimbal_small_3d_2:
'''
214         <plugin name="GstCameraPlugin"
215             filename="GstCameraPlugin">
216           <udp_host>127.0.0.1</udp_host>
217           <udp_port>5700</udp_port>
218           <use_basic_pipeline>true</use_basic_pipeline>
219           <use_cuda>false</use_cuda>
220         </plugin>
'''

and so on...


> If you need to send the camera feed to different ip addresses, you can edit the '''<udp_host>127.0.0.1</udp_host>''' parameter to the IP of the device you want to access the stream. Now the cameras should be set up.

#### Testing the Cameras

> This section is an expansion of the official Ardupilot Gazebo Plugin [README's](https://github.com/ArduPilot/ardupilot_gazebo) section on accessing the cameras.

A simple way to test the camera streams is to use Gstreamer directly. In order to do this, you can install Gstreamer by following the instructions [here](https://gstreamer.freedesktop.org/documentation/installing/on-linux.html?gi-language=c). Once you have installed gstreamer, you need to enable streaming for each camera you want to use. This can be done be referencing the Gazebo camera topic (there will be one for each camera included in the world file).

After opening Gazebo, use another terminal to list the Gazebo topics:

'''sh
gz topic -l
'''

You should see an entry toward the bottom like this for each drone camera in the scene:

'''
/world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming
'''

This the Gazebo topic that starts the camera stream. To enable it:

'''sh
gz topic -t /world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p "data: 1"
'''

Replace the '''/world/iris_runway/model/iris_with_gimbal_1/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming''' topic with how it is printed from your Gazebo topic list. Do this for each '''enable_streaming''' topic.


Finally, we can test the camera streams. To view a stream, run the following command with the correct '''udpsrc port''':

'''sh
gst-launch-1.0 -v udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
'''

You should get a camera feed that looks like this:
<img width="771" height="638" alt="Screenshot_20250714_135957" src="https://github.com/user-attachments/assets/757f4614-3d14-476a-8cf0-15e4316e7097" />







