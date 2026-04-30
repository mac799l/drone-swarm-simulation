"""
    Filename: udp_airsim_single_cls.py
    Author: Cameron Lira
    Project: Drone Swarm Control Using SITL and Gazebo

    Description:
    Commands a connected drone to follow a preset path defined in the control function.
    Performs classification using images from a virtual Airsim camera and YOLO.
    Uses a UDP networking backend written in C to synchronize GPS and classification labels:
    - performs a simple majority-voting consensus scheme for classification.
    - detects distance between drones (collision avoidance to be added).

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
from multiprocessing import Process, Pipe
from threading import Thread, Lock
#from functools import partial
#import socket
import json
import subprocess
import os


# Stores the local and network state objects.
state_vector = []
my_node_id = None

'''
Enumerator of detectable classes for use by a model trained on the MEDIC disaster dataset.
Can be updated to match your specific model.
'''
class Disaster(Enum):
    EARTHQUAKE = 0
    FIRE = 1
    FLOOD = 2
    HURRICANE = 3
    LANDSLIDE = 4
    NOT_DISASTER = 5
    OTHER_DISASTER = 6

'''
Defines the state class for creating local and network states.
'''
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

'''
Create a new state object with default values.
'''
def initializeState():
    new_state = state()
    new_state.set("is_valid", 0)
    new_state.set("id", 0)
    new_state.set("seq_num", 0)
    new_state.set("classification", 0)
    new_state.set("gps", [0.0, 0.0, 0.0])
    return new_state
    

'''
Connect to a drone instance (i.e. SITL forwarded connection, or physical connection).
'''
def connectCopter(connection):

    print(f"Connecting to: {connection}")

    copter = connect(connection, wait_ready=True)
    return copter


'''
Connect to the Airsim environment using the Airsim API.
Used for drone camera access.
'''
def connectAirsim(airsim_ip):

    client = airsim.MultirotorClient(ip=airsim_ip)
    client.confirmConnection()
    client.enableApiControl(True)
    return client

'''
Read camera inputs from an Airsim simulation and 
1. display images without classification.
2. display images with classification
    a. with network consensus
    b. without network consensus.
'''
def classificationYOLO(copter, airsim_ip, model_path, use_consensus, airsim_name, pipe):

    if not airsim_name or not airsim_ip:
        print("No name provided")
    airsim_client = connectAirsim(airsim_ip)
    print("Camera connected.")
    print(f"USE_CONSENSUS: {use_consensus}")

    # 1. Display images without classification.
    if not model_path:
        while True:
            frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=airsim_name)
            nparr = np.frombuffer(frame, np.uint8)
            img = cv.imdecode(nparr, cv.IMREAD_COLOR)
            cv.imshow('Camera feed',annotated_frame)

            # Press 'q' from the camera window to stop classification.
            if cv.waitKey(1) == ord('q'):
                break
    
    # 2. Display images with classification.
    else:
        DETECTION_THRESHOLD = 0.5 # 50% confidence threshold.
        model = YOLO(model_path)
        # Save data to a list (optional)
        # frame_data = []
        # frame_data.append([0,'NOT_DISASTER', 0, [0,0,0]])
        consensus_reached = True

        # a. Display classification with networking consensus features.
        if use_consensus:
            while True:
                frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=airsim_name)
                nparr = np.frombuffer(frame, np.uint8)
                img = cv.imdecode(nparr, cv.IMREAD_COLOR)

                results = model.predict(source = img, verbose = False)
                annotated_frame = results[0].plot()
                cv.imshow('Camera feed',annotated_frame)

                probabilites = results[0].probs
                top_class = probabilites.top1
                confidence = probabilites.top1conf
                location = copter.getLocationGlobal() #TODO: ACCESS FROM STATE VECTOR
                
                # Update local state. Default to NOT_DISASTER.
                if confidence >= DETECTION_THRESHOLD:
                    pipe.send(top_class)
                else:
                    pipe.send(Disaster.NOT_DISASTER.value)

                states = pipe.recv()

                # TODO: determine consensus only on valid states, i.e. timeouts.
                majority_vote = max(set(states), key=states.count)
                #print(f"States: {states}")
                #print(f"Majority vote: {majority_vote} - Count: {states.count(majority_vote)}")

                # Don't output if consenus is NOT_DISASTER or not a majority.
                if majority_vote != Disaster.NOT_DISASTER.value and states.count(majority_vote) >= (len(states)):
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
                frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=airsim_name)
                nparr = np.frombuffer(frame, np.uint8)
                img = cv.imdecode(nparr, cv.IMREAD_COLOR)

                results = model.predict(source = img, verbose = False)
                annotated_frame = results[0].plot()
                cv.imshow('Camera feed',annotated_frame)

                probabilites = results[0].probs
                top_class = probabilites.top1
                confidence = probabilites.top1conf
                enum_name = Disaster(top_class).name
                location = copter.getLocationGlobal() #TODO: ACCESS FROM STATE VECTOR

                # Update local state. Default to NOT_DISASTER.
                if confidence >= DETECTION_THRESHOLD:
                    pipe.send(top_class)
                    #state_vector[0].set("classification", top_class)
                else:
                    pipe.send(Disaster.NOT_DISASTER.value)
                    #state_vector[0].set("classification", Disaster.NOT_DISASTER.value)

                states = pipe.recv() # Not used.
                
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


''' 
Defines the drone's flight path and login.
'''
def droneControl(copter):
    
    print(f"Copter: {copter}")

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    #copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(25)

    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 5, velocity_z = 0, duration = 15)
    time.sleep(1)
    copter.send_global_ned_velocity(velocity_x = -15, velocity_y = -5, velocity_z = 0, duration = 15)

    copter.go_to(copter.getHome())
    time.sleep(2)
    
    copter.land()
    return

'''
Defines CLI arguments and options.
'''
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

'''
Convert a serialized JSON object to a dictionary.
'''
# def jsonToState(data):
#     msg_json = json.loads(data.decode())
#     ip = msg_json.get("ip")
#     cls = msg_json.get("cls")
#     gps = msg_json.get("gps")
#     return 0

'''
Convert a state dictionary object to serialized JSON for transmission.
'''
def stateToJSON(state):
    msg_json = {"classification": state.get("classification"),
                 "gps": state.get("gps")}
    #print(f"5. msg_json: {msg_json}")
    msg_json = json.dumps(msg_json).encode() + b'\n'
    return msg_json

'''
Monitor pipe for updated states from the network process.
'''
async def listenServerPipe(fd):
    loop = asyncio.get_running_loop()
    
    with os.fdopen(fd, 'rb') as pipe:
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, pipe)

        while True:
            raw = await reader.readline()
            if not raw:
                break

            try:
                msg = json.loads(raw.decode().strip())
            except json.JSONDecodeError:
                continue

            node_id = msg["id"]

            #print(f"Reading state update for node {node_id}")
            #print(f"Updating state vector from network process: {msg}.")

            state_vector[node_id].set("is_valid", msg["is_valid"])
            state_vector[node_id].set("classification", msg["classification"])
            state_vector[node_id].set("gps", msg["gps"])



'''
Monitor the classification process pipe for new data.
Send current state vector back for consensus.
'''
async def clsPipe(mp_pipe):
    # Create event.
    data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(mp_pipe, data_available.set)
    
    # Monitor pipe.
    while True:
        while not mp_pipe.poll():
            await data_available.wait()
            data_available.clear()
        
        # Recieve new classification enum.
        msg = mp_pipe.recv()
        #print(f"2 Received data from CLS process: {msg}.")
        state_vector[my_node_id].set("classification", msg)
        states = []
        for i in range(len(state_vector)):
            states.append(state_vector[i].get("classification"))
        #print(f"2 Sending data to CLS process {states}.")
        mp_pipe.send(states)

'''
Send local state to the network process.
'''
async def sendServerPipe(os_pipe):
    while True:
        
        #for _ in range(len(state_vector)):
        #print("3 Sending data to network process:")
        msg = stateToJSON(state_vector[my_node_id])
        #msg = json.dumps(msg).encode() + b'\n'
        os.write(os_pipe, msg)
        await asyncio.sleep(1) # TODO: use signals.


async def ipc(r_vector, w_local, parent_pipe):
    results = await asyncio.gather(
        listenServerPipe(r_vector),
        sendServerPipe(w_local),
        clsPipe(parent_pipe)
    )
    return results

'''
Main function.
'''
def main():
    args = argParser()

    clients = []
    if args.clients_file:
        with open(args.clients_file, 'r') as file:
            line = file.readline()
            ip, port = line.split(':')
            clients.append([ip, port])
    elif args.clients:
        for client in args.clients:     
            ip, port = client.split(':')
            clients.append([ip, port])
        print(f"Clients: {clients}")

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
    num_clients = len(clients)
    for i, client in enumerate(clients): # Number of nodes.
        if f"{client[0]}:{client[1]}" == args.server[0]:
            global my_node_id
            my_node_id = i
        state_vector.append(initializeState())

    # Connect to drone instance.
    copter_connection = connectCopter(args.connection)
    copter = drone(copter_connection, state_vector, args.avoidance) # Drone class object.
    print("Copter connected.")

    # Define process for handling image gathering and classification.
    parent_pipe, child_pipe = Pipe()
    cls_process = Process(
        target=classificationYOLO,
        args=(copter, args.airsim_ip, model_path, consensus, copter_name, child_pipe,)
    )
    
    # Define thread for drone movement commands (pre-determined currently).
    ctrl_thread = Thread(target=droneControl, args=(copter,))

    processes = [cls_process, ctrl_thread]

    for process in processes:
        print(f"Starting {process} process!")
        process.start()

    # Handle server/client functionality.
    udp_server = None

    if network_enabled:
        r_local, w_local = os.pipe()
        r_vector, w_vector = os.pipe()
        udp_server = subprocess.Popen(["./udp_server", 
                       str(args.server[0]), 
                       str(r_local),
                       str(w_vector),
                       str(num_clients),
                       *map(str, args.clients)],
                       pass_fds=(r_local, w_vector))
        
        # Send and recieve data from server process pipes.
        asyncio.run(
            ipc(r_vector, w_local, parent_pipe),
        )
    else:
        asyncio.run(
            clsPipe(parent_pipe)
        )

    for process in processes:
        process.join()

    udp_server.terminate()

    try:
        udp_server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        udp_server.kill()
        udp_server.wait()

    time.sleep(1)
    print("Finished script. Connections closed.")


if __name__ == "__main__":
    main()

