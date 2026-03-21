"""
    Filename: airsim_single_uav_classification.py
    Author: Cameron Lira
    Updated: 2026-02-24
    Project: Drone Swarm Control Using SITL and Gazebo

    Description:
    Commands a connected drone to follow a preset path defined in the control function.
    Performs classification using images from a virtual Airsim camera and YOLO.
    Implements a simple drone network for drone swarm coordination:
    - Uses a simple majority-voting scheme to accomplish classification consensus.
    - Detects distance between drones (collision avoidance to be added).

    NOTE: the script is currently designed to perform YOLO classification using a YOLO model trained on the MEDIC disaster dataset.
    Minor modifications would be needed to perform other tasks.

    
    Positional arguments:
    connection            The IP:PORT of the drone connection (i.e. Mavproxy forwarded UDP connection).
    airsim                The IP of the host running Airsim.

    Options:
    -h, --help            show this help message and exit
    -p PATH, --model-path PATH
                            The full path of a YOLO CLS model to perform classification on the drone camera images. Enables classification.
    -s SERVER, --server-ip SERVER
                            The IP:PORT for the drone communication server.
    -c [CLIENTS], --client-ips [CLIENTS]
                            The IP:PORT's of the client machines for drone communication.
    -n NAME, --copter-name NAME
                            The name of the drone you are accessing (i.e. in Airsim settings.json).
    --no-networking       Disable drone networking features.
    --no-consensus        Disable drone consensus for classification.
    --no-avoidance        Disable drone proximity detection (collision avoidance to be added).

"""

from collections import abc
import collections
collections.MutableMapping = abc.MutableMapping
from dronekit import connect
from droneclass_dk import drone
import time
import argparse
import cv2 as cv
from ultralytics import YOLO
from enum import Enum
import airsim
import numpy as np
#from drone_network import swarm
import asyncio
from multiprocessing import Process, Value, Pipe
from threading import Thread, Lock
from functools import partial
import socket
import json
import subprocess
import os


# Share states globally for ease of access in threads.
# state_vector[0] is the local state.
state_vector = []

# Detected classes for use by a YOLO model trained on the MEDIC disaster dataset.
# Can be updated to match your specific model.
class Disaster(Enum):
    EARTHQUAKE = 0
    FIRE = 1
    FLOOD = 2
    HURRICANE = 3
    LANDSLIDE = 4
    NOT_DISASTER = 5
    OTHER_DISASTER = 6

# Define state class for creating state objects.
class state:
    def __init__(self):
        self._data = {}
        self._lock = Lock()
    
    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key, value):
        with self._lock:
            self._data[key] = value
    
    def delete(self, key):
        with self._lock:
            del self._data[key]

def initializeState():
    new_state = state()
    new_state.set("is_valid", 0)
    new_state.set("id", 0)
    new_state.set("seq_num", 0)
    new_state.set("classification", 0)
    new_state.set("gps", [0.0, 0.0, 0.0])
    return new_state
    

# Connect to the drone.
def connectCopter(CONNECTION):

    print(f"Connecting to: {CONNECTION}")

    copter = connect(CONNECTION, wait_ready=True)
    return copter


# Connected to camera stream.
def connectAirsim(AIRSIM_IP):

    client = airsim.MultirotorClient(ip=AIRSIM_IP)
    client.confirmConnection()
    client.enableApiControl(True)

    return client

# args=(child_cls, cls_enum, copter, args.airsim_ip, args.path, consensus, copter_name,)
# Perform classification on the camera stream.
def classificationYOLO(copter, AIRSIM_IP, MODEL_PATH, USE_CONSENSUS, NAME):

    airsim_client = connectAirsim(AIRSIM_IP)
    print("Camera connected.")
    print(f"USE_CONSENSUS: {USE_CONSENSUS}")

    # 1. Display images without classification.
    if not MODEL_PATH:
        while True:
            frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=NAME)
            nparr = np.frombuffer(frame, np.uint8)
            img = cv.imdecode(nparr, cv.IMREAD_COLOR)
            cv.imshow('Camera feed',annotated_frame)

            # Press 'q' from the camera window to stop classification.
            if cv.waitKey(1) == ord('q'):
                break
    # 2. Display images with classification.
    else:
        DETECTION_THRESHOLD = 0.5 # 50% confidence threshold.
        model = YOLO(MODEL_PATH)
        # Save data to a list (optional)
        # frame_data = []
        # frame_data.append([0,'NOT_DISASTER', 0, [0,0,0]])
        consensus_reached = True

        # a. Display classification with networking consensus features.
        if USE_CONSENSUS:
            while True:
                frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=NAME)
                nparr = np.frombuffer(frame, np.uint8)
                img = cv.imdecode(nparr, cv.IMREAD_COLOR)

                results = model.predict(source = img, verbose = False)
                annotated_frame = results[0].plot()
                cv.imshow('Camera feed',annotated_frame)

                probabilites = results[0].probs
                top_class = probabilites.top1
                confidence = probabilites.top1conf
                location = copter.getLocationGlobal()
                
                # Update local state. Default to NOT_DISASTER.
                if confidence >= DETECTION_THRESHOLD:
                    state_vector[0].set("classification", top_class)
                else:
                    state_vector[0].set("classification", Disaster.NOT_DISASTER.value)

                if confidence > DETECTION_THRESHOLD:
                    # Check consensus.
                    count = 1
                    for i in range(len(state_vector) - 1):
                        cls = state_vector[i+1].get("classification")
                        if top_class == cls and enum_name != 'NOT_DISASTER':
                            count += 1

                    # TODO: determine consensus only on valid states, i.e. timeouts.
                    if count >= (len(state_vector) // 2):
                        print("Detected class:", Disaster(top_class).name,
                            " -- Confidence:",'{0:.2f}'.format(confidence.item()), 
                            " -- GPS:", location)
                        
                        ''' OPTIONALLY SAVE DATA.           
                        if enum_name != frame_data[-1][1]:
                            frame_data.append([frame, enum_name, confidence, location])
                        elif frame_data[-1][2] < confidence:
                            frame_data.pop()
                            frame_data.append([frame, enum_name, confidence, location])
                        '''

                # Press 'q' from the camera window to stop classification.
                if cv.waitKey(1) == ord('q'):
                    break
        
        # b. Display classification without using consensus.
        else:
            while True:
                frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=NAME)
                nparr = np.frombuffer(frame, np.uint8)
                img = cv.imdecode(nparr, cv.IMREAD_COLOR)

                results = model.predict(source = img, verbose = False)
                annotated_frame = results[0].plot()
                cv.imshow('Camera feed',annotated_frame)

                probabilites = results[0].probs
                top_class = probabilites.top1
                confidence = probabilites.top1conf
                enum_name = Disaster(top_class).name
                location = copter.getLocationGlobal()

                # Update local state. Default to NOT_DISASTER.
                if confidence >= DETECTION_THRESHOLD:
                    state_vector[0].set("classification", top_class)
                else:
                    state_vector[0].set("classification", Disaster.NOT_DISASTER.value)

                if confidence > DETECTION_THRESHOLD:
                    print("Detected class:", enum_name ,
                          " -- Confidence:",'{0:.2f}'.format(confidence.item()), 
                          " -- GPS:", location)
                    
                    ''' OPTIONALLY SAVE DATA.           
                    if enum_name != frame_data[-1][1]:
                        frame_data.append([frame, enum_name, confidence, location])
                    elif frame_data[-1][2] < confidence:
                        frame_data.pop()
                        frame_data.append([frame, enum_name, confidence, location])
                    '''

                # Press 'q' from the camera window to stop classification.
                if cv.waitKey(1) == ord('q'):
                    break

    cv.destroyAllWindows()
    return


# Controls the drone's flight path.
def droneControl(copter):
    
    print(f"Copter: {copter}")

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    #copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(15)
    time.sleep(1)
    copter.land()
 
    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 5, velocity_z = 0, duration = 15)
    time.sleep(1)
    copter.send_global_ned_velocity(velocity_x = -15, velocity_y = -5, velocity_z = 0, duration = 15)

    copter.go_to(copter.getHome())
    time.sleep(2)
    
    copter.land()
    return

def argParser():

    parser = argparse.ArgumentParser(description='Airsim drone script with optional networking features.')
    parser.add_argument(
        'connection',
         type=str,
         help="The PROT:IP:PORT of the drone connection (i.e. Mavproxy forwarded UDP connection)."
    )
    parser.add_argument(
        'airsim_ip',
         type=str,
         help="The IP of the host running Airsim."
    )
    parser.add_argument(
        '-p', '--model-path',
         type=str,
         dest='model_path',
         nargs=1,
         help="The path of a YOLO CLS model to perform classification on the drone camera images. Enables YOLO classification."
    )
    parser.add_argument(
        '-s', '--server-ip',
         type=str,
         dest='server',
         nargs=1,
         help="The IP:PORT for the drone communication server. Enables networking."
    )
    parser.add_argument(
        '-c', '--client-ips',
         type=str,
         dest='clients',
         nargs='*',
         help="The IP:PORT's of the client machines in the network. Enables networking."
    )
    parser.add_argument(
        '-r', '--read-client-ips',
         type=str,
         dest='clients_file',
         nargs=1,
         help="The path of a file with the IP:PORT's of the client machines in the network. Enables networking."
    )
    parser.add_argument(
        '-n', '--copter-name',
         type=str,
         dest='copter_name',
         nargs=1,
         help="The name of the Airsim drone you want to connect to for the camera (i.e. 'Copter0' in the Airsim settings.json)."
    )
    parser.add_argument(
         '--no-consensus',
         action='store_false',
         dest='consensus',
         help="Disable drone consensus for classification."
    )
    parser.add_argument(
         '--no-avoidance',
         action='store_false',
         dest='avoidance',
         help="Disable drone proximity detection."
    )
    parser.add_argument(
         '--no-camera',
         action='store_false',
         dest='camera',
         help="Disable drone camera, classification, and consensus."
    )

    args = parser.parse_args()
    
    return args

def jsonToState(data):
    msg_json = json.loads(data.decode())
    ip = msg_json.get("ip")
    cls = msg_json.get("cls")
    gps = msg_json.get("gps")
    return 0

def stateToJSON(state):
    msg_json = {"ip": state.ip, "cls": state.cls, "gps": state.gps}
    msg_json = json.dumps(msg_json).encode() + b'\n'
    return msg_json

async def listenServerPipe(pipe):
    while True:
        msg = pipe.readline()
        msg = msg.decode().strip()
        id = msg["id"] + 1
        state_vector[id].set("is_valid", msg["is_valid"])
        state_vector[id].set("classification", msg["classification"])
        state_vector[id].set("gps", msg["gps"])


async def sendServerPipe(pipe):
    while True:
        for _ in range(len(state_vector)):
            msg = json.dumps(state_vector[0]).encode() + b'\n'
            pipe.send(msg)
        asyncio.sleep(1) # TODO: use signals.

def main():

    args = argParser()
    copter_connection = connectCopter(args.connection)
    copter = drone(copter_connection) # Drone class object.
    print("Copter connected.")

    clients = []
    if args.clients_file:
        with open(args.clients_file, 'r') as file:
            line = file.readline
            ip, port = line.split(':')
            clients.append([ip, port])
    elif args.clients:
        for client in args.clients:     
            ip, port = client.split(':')
            clients.append([ip, port])
        print(clients)

    if args.server and clients:
        print("Networking enabled.")
        network_enabled = True
    else:
        print("Missing server or client addresses.\nNetworking disabled.")
        network_enabled = False
    
    consensus = False
    if network_enabled and args.consensus:
        consensus = True

    # A name is required for accessing the Airsim camera (set in Airsim settings).
    # Defaults to 'Copter'
    if not args.copter_name:
        print("No name given for Airsim copter, defaulting to 'Copter'.")
        copter_name = 'Copter'
    else:
        copter_name = args.copter_name[0]

    model_path = None
    try:
        model_path = args.model_path[0]
    except:
        model_path = None

    # Initialize state vector.
    for _ in range(num_clients + 1):
        state_vector.append(initializeState())

    # Handle image gathering and classification.
    cls_process = Process(
        target=classificationYOLO,
        args=(copter, args.airsim_ip, model_path, consensus, copter_name,)
    )
    
    # Direct drone path.
    ctrl_thread = Thread(target=droneControl, args=(copter,))

    processes = [cls_process, ctrl_thread]

    for process in processes:
        print(f"Starting {process} process!")
        process.start()

    num_clients = len(clients)
    # Handle server/client functionality.
    udp_server = None

    if network_enabled:
        r_local, w_local = os.pipe()
        r_vector, w_vector = os.pipe()
        udp_server = subprocess.Popen(["./udp_server", 
                       args.server[0], 
                       r_local,
                       w_vector,
                       num_clients,
                       *clients],
                       pass_fds=(r_local, w_vector))
        
        subprocess.run(udp_server)
        # Send and recieve data from server process pipes.
        asyncio.gather(
            listenServerPipe(r_vector),
            sendServerPipe(w_local)
        )

    for process in processes:
        process.join()

    time.sleep(1)
    print("Finished script. Connections closed.")


if __name__ == "__main__":
    main()

