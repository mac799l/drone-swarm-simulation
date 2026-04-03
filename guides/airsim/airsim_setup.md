## Overview (WIP)

In order to test drones in a 3D simulated environment, this guide will show the process for setting up and configuring a simple Airsim Unreal Engine environment. Unreal Engine has several advantages compared to Gazebo, such as improved graphical fidelity, weather effects, and easier environment creation. However, Gazebo is much less graphically demanding and has a much deeper robotics and simulation capability.

If you are running natively on Linux, I recommend using Gazebo for the improved performance as I found Unreal Engine to be poorly optimized on Linux. 

Either option is practical on Windows depending on your PC specifications as I had good results running Gazebo on WSL2.

## Requirements

In order to create the Airsim simulation environment as used in this guide, you will need two programs:

* Unreal Engine 5.4.4
* Visual Studio 2022

> Alternatively, Unity is supported by some versions of Airsim but this is not explored in this guide.

If you are unfamiliar with the basics of Unreal Engine, I highly recommend following the first two tutorials published by [Unreal Sensei on Youtube](https://www.youtube.com/playlist?list=PLKPWwh_viQMGQkQfKKD5lF96efA3_RWt-). For most testing purposes, you will only need a basic understanding of the interface and controls, but depending on your needs and the environments you want to create, it may be advisable to explore further tutorials.

Installation instructions for Unreal Engine 5 can be found [here](https://www.unrealengine.com/en-US/download).
> Although it is possible to run UE5 on a Linux machine, I found the performance to be significantly degraded compared to Windows, so I will be using Windows to run UE5 in this guide.

### Airsim Version Selection
Since Microsoft dropped support of the Airsim project in 2018, the [official Airsim repository](https://github.com/microsoft/AirSim) is only compatible with Unreal Engine 4. Therefore, I will be using the Codex Labs [Colessuem fork](https://github.com/CodexLabsLLC/Colosseum) in order to use Unreal Engine 5 - particularly for the new performance features, such as Nanite and Lumen, to streamline environment creation. Specifically, I have tested `UE 5.4.4`.

The official installation guide for Colesseum also makes use of the Visual Studio 2022 Developer Console, though there may be other methods of completing the Colosseum reopository cloning and building.

## Installation

After installing UE5, we can install Colloseum. I will be following the official guide, which can be found [here](https://codexlabsllc.github.io/Colosseum/build_windows/).

The first step is to clone the repository into the folder of your choice (a seperate drive, i.e. not your `C` drive, is recommended). To do this, we will open the `Visual Studio 2022 Developer Command Prompt` from the search bar.


<img width="754" height="245" alt="Screenshot 2026-01-07 222256" src="https://github.com/user-attachments/assets/8ab4a2f7-1e40-4b11-a6ef-c748fe1d79a4" />

<img width="1113" height="620" alt="Screenshot 2026-01-07 222532" src="https://github.com/user-attachments/assets/b22cda9f-70b4-4a95-a932-58532985a92c" />


If you are cloning to a drive other than your `C` drive, you can change the selected drive by inputting the drive letter you want to change to as shown below, such as changing to drive `D`:
```sh
C:\Program Files\Microsoft Visual Studio\2022\Community> 
C:\Program Files\Microsoft Visual Studio\2022\Community>D:
D:\>
```

Now clone the repository once you have navigated to the location you wish to install it. The following command will download the repository into a new folder: `Colloseum`.

```sh
git clone https://github.com/CodexLabsLLC/Colosseum.git
```
Next, go into the folder and run the following; my `build.cmd` failed without running the submodule update first.
```sh
cd Colloseum
git submodule update --init
```
Then:
```sh
build.cmd
```
This may take some time to complete.

## Initial Configuration
Now we can test the included environment in Unreal Engine. There are a few ways to do this, including adding the AirSim plugin to your own projects. However, for simplicity, I recommend using the provided environment at first.

To do this, simply navigate to `Colloseum/Unreal/Environments/BlocksV2` folder and double-click the `BlocksV2.sln` Visual Studio solution file.

Once Visual Studio opens, select the drop-down menu from the `Start` button and choose to `Configure Startup Projects...`. From there, change the startup project from `UE5` to `BlocksV2`. Now you can start the environment using the start button, which should now say: `Local Windows Debugger`:

<img width="1892" height="633" alt="Screenshot 2026-01-08 171709" src="https://github.com/user-attachments/assets/03769d47-4875-4a67-9d93-390fdaac1202" />

<img width="866" height="659" alt="Screenshot 2026-01-08 171724" src="https://github.com/user-attachments/assets/729fd9ef-842f-48f7-9158-cf71e7007904" />

The first start up will take some time, but once it completes you should see something like this:

<img width="2559" height="1392" alt="Screenshot 2026-01-08 172005" src="https://github.com/user-attachments/assets/03171ff0-5521-44dc-8327-c86afa8700ba" />

#### Drone Configuration
In contrast to Gazebo, this step is much simpler and will only require editing a single configuration file. To do this navigate to your documents folder: `Documents/Airsim/`. There should be a single `setting.json` file.

> If the folder or file does not exist, go ahead and make them. The default configuration values can be found [here](https://microsoft.github.io/AirSim/settings/). I will also provide my settings where applicable if you want to use them.

Here are my settings for a single drone:
```json
{
    "SettingsVersion": 1.2,
    "CameraDefaults": {
        "CaptureSettings": [
            {
                "ImageType": 0,
                "Width": 720,
                "Height": 360,
                "FOV_Degrees": 90,
                "AutoExposureSpeed": 100,
                "MotionBlurAmount": 0
            }
        ]
    },
    "LogMessagesVisible": true,
    "SimMode": "Multirotor",
    "OriginGeopoint": {
        "Latitude": -35.363261,
        "Longitude": 149.165230,
        "Altitude": 583
    },
    "Vehicles": {
        "Copter0": {
            "VehicleType": "ArduCopter",
            "UseSerial": false,
            "LocalHostIp": "0.0.0.0",
            "UdpIp": "",
            "UdpPort": 9003,
            "ControlPort": 9002,
            "X": 0,
            "Y": 0,
            "Z": 0
        }
    }
}
```
You will need to input the IP address of your machine running the Ardupilot simulated controller. This is explained in more detail in the next step.



## Test the Environment


### Installing the Airsim pip package.

Pip will fail to install the Airsim package due to the following error:

```bash
  error: subprocess-exited-with-error
  
  × Getting requirements to build wheel did not run successfully.
  │ exit code: 1
  .
  .
  .
  ModuleNotFoundError: No module named 'numpy'
  [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed to build 'airsim' when getting requirements to build wheel
```

So we need to make a minor modification to the `setup.py` file of the package. To do this, you will need to download the files from [PyPi](https://pypi.org/project/airsim/#files) and extract to a folder.

Now we will modify the following two lines in the `setup.py` file:

```py
from airsim import __version__

...

version=__version__,
```

Alter these two lines as follows:

```py
#from airsim import __version__

...

version="1.8.1",
```

Now install by selecting your Python virtual environment as source, and running the following command from the folder with the Airsim files:

```bash
source PATH/TO/VIRTUAL/ENVIRONMENT
pip install ./
```

If you are getting a missing module `backports` warning, you may also need to install the following package: 
```sh
pip install backports.ssl_match_hostname
```