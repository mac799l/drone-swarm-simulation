## Single Drone
We have already tested a single drone using Mavproxy commands. However, this interface is limited for more advanced purposes, so we will be using Dronekit. In order to test using the provided single drone script, some additional options need to be specified.

> Note: Dronekit is a handy library for learning to code drone behaviour, but it lacks support and maintenance so I will be transitioning this guide to Pymavlink and MAVSDK.

Run Gazebo same as before:
```sh
gz sim -v4 -r iris_runway.sdf
```

Run SITL, but add the ```--out``` option to specify a forwarding IP and port for our code to connect to:

```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --out udp:127.0.0.1:14550
```

> Note: ```--map``` and ```--console``` can be added back if desired.

Now you can run the provided code as follows (while connected to the ardupilot virtual environment as source):

```sh
python single_uav_script.py --connect udp:127.0.0.1:14550
```

### DroneKit

The Dronekit code provided creates a drone class with various simple commands that can be called on the drone object. The default main function simply makes the drone fly Northeast, then Northwest, and finally returns to the home location of the drone (saved as the takeoff location) and lands.

## Multiple Drones
> Note: this section is a modified version of the guide found [here](https://github.com/monemati/multiuav-gazebo-simulation).

In order to run multiple drones in Gazebo, some additional modifications need to be made. Firstly, go to your Ardupilot plugin models folder:

```sh
cd gz_ws/src/ardupilot_gazebo/models/
```

Now, you should see several vehicle model folders. Copy the ```iris_with_gimbal``` model for as many drones as you wish to create. I recommend leaving the original folder unaltered and creating ```iris_with_gimbal_x``` folders for each drone to be simulated (i.e. ```iris_with_gimbal_1``` and ```iris_with_gimbal_2``` and so on).

> Note: I have also provided a models folder with four models for the drones, which can be copied to your models directory to save time.

```sh
cp iris_with_gimbal iris_with_gimbal_1
```

Now, within each new ```iris_with_gimbal_x``` folder, change the ```<model name="iris_with_gimbal">``` option to ```<model name="iris_with_gimbal_X">``` where ```X``` is the number of the drone matching the folder name. Also, note the section ```<plugin name="ArduPilotPlugin"```. It should look something like this:

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
The multi-uav script uses the ```connections.txt``` to read the IP addresses and ports of each connection (currently configured for four drones). No additional changes need to be made to it, unless you have altered the ```--out``` parameters in the SITL terminals below, which specify the fordwarding port from Mavproxy. The script has each drone fly away from the starting position in a different direction and then return to the GPS coordinate from where it launched, much like the single-uav script. However, the script uses multithreading so the operation of each drone happens simultaneously. Each drone is controlled by its respective ```drone_control``` function.

Now we can launch Gazebo with the new environment (recall that we didn't change the name):

```sh
gz sim -v4 -r iris_runway.sdf
```

> Note: if you get instability with the drones - random shaking, etc. - you can try starting the SITL instances before launching Gazebo.

To run the code, open a new terminal for each drone. Now, with the Python virtual environment set as the source in each window, create the SITL instance and connect them to Gazebo:

In terminal #1:
```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0 --out udp:127.0.0.1:14550
```
In terminal #2:
```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I1 --out udp:127.0.0.1:14560
```
In terminal #3:
```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I2 --out udp:127.0.0.1:14570
```
In terminal #4:
```sh
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I3 --out udp:127.0.0.1:14580
```

Now, in another terminal, go to the directory with the ```multi_uav_script.py``` and the ```connection.txt``` files and run the following command:

```sh
python multi_uav_script.py
```
> Remember to have the ```venv_ardupilot``` virtual environment set as the source.

Now the drones should takeoff, go in different directions and then return to the starting position. It is also possible to create all the drones from a single `sim_vehicle.py` instance using the ```--count``` command, but it caused issues with my multi-uav script, so I currently recommend using seperate terminals if you use that.