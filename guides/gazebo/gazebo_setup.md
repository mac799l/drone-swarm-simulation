# Installation

This section assumes you have installed Ubuntu 22.04 (or an official [Ubuntu 22.04 flavor](https://ubuntu.com/desktop/flavors)) either natively or through Windows WSL2. If not, a guide can be found [here](https://ubuntu.com/tutorials/install-ubuntu-desktop#1-overview). The Windows WSL2 installation guide can be found [here](https://learn.microsoft.com/en-us/windows/wsl/install).

## Gazebo
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

<p align="center">
  <img src="https://github.com/user-attachments/assets/8ef2dcf4-07ae-464d-af67-d88400c01d89" width="808" height="700">
</p>

> Note: if the window fails to open, check the debug information from the terminal you started Gazebo in. If it reads
> ```[GUI] [Dbg] [Gui.cc:343] GUI requesting list of world names. The server may be busy downloading resources. Please be patient.```
> Then the issue is with your firewall configuration. To correct the issue, run the following commands to allow Gazebo through the firewall:
> ```sh
> sudo ufw allow in proto udp to 224.0.0.0/4
> sudo ufw allow in proto udp from 224.0.0.0/4
> ```

Now you have a fully-functioning Gazebo installation. But more configuration work will be required to make it work with SITL and simulate drones.

## SITL
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


## Ardupilot Gazebo Plugin
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

<p align="center">
  <img src="https://github.com/user-attachments/assets/5c9b4333-e755-4f72-8b3f-f2369da80833" width="808" height="700">
</p>

Now the Gazebo Plugin should be working.

## Testing the Environment

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

These commands should start your drone motors (arm) and make it ascend to 15 meters in the Gazebo window. If an error occurs (i.e. the drone is not armable, etc.), then wait a few moments and try again, the drone may still be initializing. 

Now the drone should be fully functional, though Mavproxy commands are not the preferred way to control the drone long term. More advanced drone control methods - and how to set up multiple drones - are detailed in the `gazebo_drone_swarm` and `gazebo_cameras` guides.


## Python Virtual Environment Setup
Now to set up the Python virtual environment so we can run some code. To do this ensure you are connected to the venv-ardupilot virtual environment:
```sh
source ~/venv-ardupilot/bin/activate
```

Now, ensure the following packages are installed:

```sh
pip install pymavlink dronekit MAVProxy
```

Now that the environment is setup, we can expand into controlling multiple drones, writing scripts, and implementing machine vision.