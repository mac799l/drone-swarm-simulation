# Drone Swarm Control Using SITL and Gazebo
This is a code base and setup guide for Software in the Loop (SITL) virtual drone swarm control research using Gazebo-Harmonic (TODO: or Airsim).

## Background
Before testing scripts and commands in the field (with real, and expensive, drones), it is a good idea to create virtual environments and simulated vehicles first. The end goal is to test scripts, code, and techniques which are then usable in the real world with actual drones. To that end, this guide will follow the process of getting such a setup working using SITL and Gazebo-Harmonic.
> Note: this guide specifically uses drone models and simulations, but others vehicle types can be set up similarly.

## Pre-requisites

### Recommended Specifications

### Ubuntu 22.04

For running the simulation, the guide uses a Ubuntu 24.04 installation (the Kubuntu offical flavor) installed natively, but Windows can also be used by leveraging WSL2 (Windows Subsystem for Linux 2).


# Installation

## Ubuntu 22.04
> This section assumes you have installed Ubuntu 22.04 (or an official [Ubuntu flavor]()). If not a guide can be found [here](). The Windows installation guide is in the next section.

### Gazebo

### SITL
Once the repository has been cloned, and the setup script has been run, the next step is to build the vehicle. To do this, you will need to connect to the python virtual environment first:
```sh source ~/venv-ardupilot/bin/activate ```
This ensures that you are using the Python virtual environment created by Ardupilot. Now, run the following command to generate a copter drone:
```sh sim_vehicle.py -v ArduCopter ```
> On the first run this will compile the vehicle and may take some time.

Once that is completed, some information about the drone should come up in the console (as well as an additional console interface with connection information). SITL should now be working.

### Ardupilot Plugin

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

