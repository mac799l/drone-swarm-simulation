# Drone Swarm Control Using SITL and Gazebo
Before testing scripts and commands in the field (with real, and expensive, drones), it is possible to test in virtual environments and simulated vehicles first. The end goal is to test scripts, code, and techniques in a safe and easily replicable environment, which are then usable in the real world with actual drones. To that end, this guide will follow the process of getting a simple virtual environement and drone setup working using Ardupilot SITL and Gazebo-Harmonic.
> Note: this guide specifically uses drone models, but other vehicle types can be set up in a similar way.

## Pre-requisites
* A reasonably capable computer (I recommend a multicore CPU, dedicated GPU, and at least 8GB of ram)
* Ubuntu 22.04 or Windows with WSL2
> Note: other versions of Ubuntu may also work, but were not tested.

# Installation

## Ubuntu 22.04
> This section assumes you have installed Ubuntu 22.04 (or an official [Ubuntu flavor]()). If not a guide can be found [here](). The Windows installation guide is in the next section.

### Gazebo
> Note: this section closely follows the official guide, which can be found [here](https://gazebosim.org/docs/harmonic/install_ubuntu/).

Ensure Ubuntu is up to date and install necessary packages:
```sh
sudo apt-get update
sudo apt-get install curl lsb-release gnupg
```
Install Gazebo:
```sh
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update
sudo apt-get install gz-harmonic
```

Run Gazebo:
```sh
gz sim -v4 -r shapes.sdf
```
> * gz is calling the Gazebo installation.
> * sim specifies the Gazebo mode.
> * The -v4 option prints debugging information to the console.
> * -r name.sdf specifies the environment to load.

This command should open Gazebo with a window like this:
ADD PICTURE

> Note: if the windows fails to open, check the debug information from the console you started Gazebo in. If it reads
> ```[GUI] [Dbg] [Gui.cc:343] GUI requesting list of world names. The server may be busy downloading resources. Please be patient.```
> Then the issue is with your firewall configuration. To correct the issue, run the following commands to allow Gazebo through the firewall:
> ```sh
> sudo ufw allow in proto udp to 224.0.0.0/4
> sudo ufw allow in proto udp from 224.0.0.0/4
> ```

Now you have a fully-functioning Gazebo installation. But more configuration work will be required to make it work with SITL and simulate drones.

### SITL
Once the repository has been cloned, and the setup script has been run, the next step is to build the vehicle. To do this, you will need to connect to the python virtual environment first:

```sh 
source ~/venv-ardupilot/bin/activate
```

This ensures that you are using the Python virtual environment created by Ardupilot. Now, run the following command to generate a copter drone:

```sh 
sim_vehicle.py -v ArduCopter
```

> On the first run this will compile the vehicle and may take some time.

Once that is completed, some information about the drone should come up in the console (as well as an additional console interface with connection information). SITL should now be working.

### Ardupilot Plugin
Ensure dependencies are installed (this may not need to install anything).
```sh
sudo apt update
sudo apt install libgz-sim8-dev rapidjson-dev
sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
```

Create a directory for the plugin and clone the repository:
```sh
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

Configure environment variables so Gazebo can access the plugin:

```sh
echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/gz_ws/src/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}' >> ~/.bashrc
echo 'export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}' >> ~/.bashrc
```
> Note: if the '''gz sim''' command does not work, a system restart may be needed.


## Windows (WSL2)
> This section assumes you have installed Windows and WSL2. If not, the guide can be found [here]().

# Set Up

## Python Virtual Environment

## Gazebo-Harmonic

## Ardupilot SITL


# Configuration

## Gazebo

## SITL


# Running The Simulation

## Ardupilot Commands

