##Drone Swarm Control Using SITL and Gazebo
This is a code base and setup guide for Software in the Loop (SITL) virtual drone swarm control research using Gazebo-Harmonic (TODO: or Airsim).

#Background
Before testing scripts and commands in the field (with real, and expensive, drones), it is a good idea to create virtual environments and simulated vehicles first. The end goal is to test scripts, code, and techniques which are then usable in the real world with actual drones. To that end, this guide will follow the process of getting such a setup working using SITL and Gazebo-Harmonic.
> Note: this guide specifically uses drone models and simulations, but others vehicle types can be set up similarly.

#Pre-requisites
For running the simulation, the guide uses a Ubuntu 24.02 installation (the Kubuntu offical flavor)
