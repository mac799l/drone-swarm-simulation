# Drone Swarm Control Using SITL and Gazebo (WIP)
Before testing drone control scripts or GCS (ground control station) commands in the field with real - and expensive - drones, it is possible to test in simulated environments with virtual vehicles first. The goal of this guide is to create scripts and techniques in a safe, virtual, and easily replicable environment - much of which is transferrable to the real world with actual drones. To that end, this guide will demonstrate the following the process:
* (1). Setting up a simulated environment and drone controller.
* (2). Creating simple control scripts.
* (3). Adding multiple drones to a single environemnt.
* (4). Accessing cameras and video streams for machine vision tasks.

This guide was created as part of a Summer 2025 Engineering Undergraduate Research Fellowship at the University of Kentucky at the Secure Decentralized Systems Laboratory under the supervision of Dr. Yang Xiao.

> This repository is a work-in-progress with additional code and documentation planned. Some planned additions:
> * Multi-drone simulations using Airsim to afford easier environment creation.
> * Additional coding scripts to better incorporate classification/object detection.
> * Rewriting scripts using MAVSDK (C++) and Pymavlink (Python) due to limited Dronekit support.
>
> Also, this guide specifically uses quadcopter drone models, but other vehicle types can be set up in a similar way.


## Pre-requisites
* Minimum specifications for Gazebo-Harmonic or Unreal Engine 5.4.
* Hardware acceleration for machine vision (if desired).
* Ubuntu 22.04 or Windows with WSL2 (with Ubuntu installed).
> Note: other versions of Ubuntu may also work, but were not tested.

## Simulators
The first step is to choose your simulated environment - Gazebo or Airsim (this guide uses the Colesseum fork) - both of which are overviewed below.

### Gazebo
Gazebo is a popular robotics simulator. It allows for the simulation of detailed vehicles, drones, and robots. These simulations include physics, sensors and cameras, and even the individual components and motors of your robot. Gazebo offers a more in-depth simulation, but has a steeper learning curve than Unreal.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fca8dfa0-4d5b-4d6a-8b07-68a609e6c8dc" width="640" height="360">
</p>

> Gazebo image [source](https://gazebosim.org/showcase)

Pros:
* Simple to set up a basic environment, especially if using Windows (no need to transmit data between WSL and Windows).
* Less GPU-intensive than Unreal Engine.
* Near limitless customization and configuration.
* ROS integration.

Cons:
* More advanced environments are harder to create.
* Multi-drone configuration is somewhat complicated.

### Airsim (Colesseum Fork)
Airsim is a plugin made for Unreal Engine 4 and developed by Microsoft. Development was halted after 2020, but several forks of the project are still maintained. The one I have chosen is called Colesseum and is maintained in part by XXXXXX. The Colleseum fork was updated to use Unreal Engine 5.4.

##############################IMAGE IMAGE IMAGE#############################

Pros:
* More user friendly interface.
* Easier to set up multiple drones.
* Unreal Engine affords useful development tools for creating environments.
* Large asset library.
* Better visual fidelity.

Cons:
* More GPU-intensive than Gazebo.
* Simulations are less realistic.
* Less customization potential.


## Other tools

### SITL
Ardupilot's SITL is a tool that allows us to simulate the inner workings of the drone itself. Sensor data such as GPS location, various status and safety checks, battery level, and more are simulated. Additionally, SITL allows us to use real-world methods (e.g. [Mavlink messages](https://mavlink.io/en/)) to control the drone using the simulated drone controller.

<p align="center">
  <img src="https://github.com/user-attachments/assets/4887f7e6-70c2-4b34-8aac-bdccba13c87d" />
</p>

> SITL image [source](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)

### Mavproxy
Mavproxy is a command line GCS affording us simple commands, connection forwarding, and other utilities - such as a satellite map. Mavproxy is a powerful tool and the default interface Ardupilot's SITL uses to connect to the drone. We will largely be using it to specify the address of the simulator, forward the drone connection to our scripts.

##############################IMAGE IMAGE IMAGE#############################


## Guide Layout
There are two main folders in this repository: `scripts` and `guides`. Contained within the `scripts` folder is code that you can use to test functionality or use a reference to get up and running in your simulation. Within that folder, there are two subfolders: `airsim` and `gazebo`. The scripts that exclusively control drone movements are identical across the two folders, but those involving the drone cameras or machine vision tasks are not. The `guides` folder is set up in a similar way.

