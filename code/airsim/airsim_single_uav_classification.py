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
from threading import Thread
from functools import partial
import socket
import json


# Map of ip/port values to their reader/writer streams.
connections = {}

# Detected classes for use by a YOLO model trained on the MEDIC dataset.
# Can be updated to match your specific model.
class Disaster(Enum):
    EARTHQUAKE = 0
    FIRE = 1
    FLOOD = 2
    HURRICANE = 3
    LANDSLIDE = 4
    NOT_DISASTER = 5
    OTHER_DISASTER = 6


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
def classificationYOLO(pipe, cls_enum, copter, AIRSIM_IP, MODEL_PATH, USE_CONSENSUS, NAME):

    airsim_client = connectAirsim(AIRSIM_IP)
    print("Camera connected.")
    print(f"USE_CONSENSUS: {USE_CONSENSUS}")
    # Display image without classification.
    if not MODEL_PATH:
        while True:
            frame = airsim_client.simGetImage('0', airsim.ImageType.Scene, vehicle_name=NAME)
            nparr = np.frombuffer(frame, np.uint8)
            img = cv.imdecode(nparr, cv.IMREAD_COLOR)
            cv.imshow('Camera feed',annotated_frame)

            # Press 'q' from the camera window to stop classification.
            if cv.waitKey(1) == ord('q'):
                pipe.send('__CLOSE__')
                break
    # Display camera feed with classification.
    else:
        DETECTION_THRESHOLD = 0.5
        model = YOLO(MODEL_PATH)
        frame_data = []
        frame_data.append([0,'NOT_DISASTER', 0, [0,0,0]])
        consensus_reached = True
        time.sleep(5)

        # Display classification with networking consensus features.
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
                enum_name = Disaster(top_class).name
                location = copter.getLocationGlobal()

                if confidence >= DETECTION_THRESHOLD:
                    cls_enum.value = top_class
                else:
                    # Default to NOT_DISASTER.
                    cls_enum.value = 5
                
                # Get consensus from other drones.
                #consensus_reached, enum_name = swarm.consensus(enum_name)
                
                print("pipe.send")
                pipe.send('CLS')
                print("pipe.recv")
                swarm_cls = pipe.recv()

                #drone_2_cls = Disaster(drone_2_cls).name
                #print(f"Drone_2_cls: {drone_2_cls}.")
                print("For loop")
                count = 0
                for cls in swarm_cls:
                    if enum_name == cls and enum_name != 'NOT_DISASTER':
                        count += 1

                if count >= len(swarm_cls) and confidence > DETECTION_THRESHOLD:
                    print("Detected class:", enum_name ,"-- Probability:",'{0:.2f}'.format(confidence.item()), " -- GPS:", location)
                    
                    ''' OPTIONALLY SAVE DATA.           
                    if enum_name != frame_data[-1][1]:
                        frame_data.append([frame, enum_name, confidence, location])
                    elif frame_data[-1][2] < confidence:
                        frame_data.pop()
                        frame_data.append([frame, enum_name, confidence, location])
                    '''

                # Press 'q' from the camera window to stop classification.
                if cv.waitKey(1) == ord('q'):
                    pipe.send('__CLOSE__')
                    break
        
        # Display classification without using consensus.
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

                if confidence >= DETECTION_THRESHOLD:
                    cls_enum.value = top_class
                else:
                    # Default to NOT_DISASTER.
                    cls_enum.value = 5

                if confidence > DETECTION_THRESHOLD:
                    print("Detected class:", enum_name ,"-- Probability:",'{0:.2f}'.format(confidence.item()), " -- GPS:", location)
                    
                    ''' OPTIONALLY SAVE DATA.           
                    if enum_name != frame_data[-1][1]:
                        frame_data.append([frame, enum_name, confidence, location])
                    elif frame_data[-1][2] < confidence:
                        frame_data.pop()
                        frame_data.append([frame, enum_name, confidence, location])
                    '''

                # Press 'q' from the camera window to stop classification.
                if cv.waitKey(1) == ord('q'):
                    pipe.send('__CLOSE__')
                    break

    cv.destroyAllWindows()

    return


# Controls the drone's flight path.
def droneControl(pipe, copter):

    print(f"Copter: {copter}")

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(15)
    
    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 5, velocity_z = 0, duration = 15, pipe=pipe)
    time.sleep(1)

    copter.send_global_ned_velocity(velocity_x = -15, velocity_y = -5, velocity_z = 0, duration = 15, pipe=pipe)

    copter.go_to(copter.getHome())
    time.sleep(2)
    
    copter.land()

    return


# Handle server and client coroutines.
async def network(cls_pipe, ctrl_pipe, cls_enum, copter, server, clients):
    send_queue = asyncio.Queue()
    await asyncio.gather(
        runServer(cls_enum, copter, server),
        *[handleServer(ip, port) for ip, port in clients],
        clsPipeReader(send_queue, cls_pipe),
        ctrlPipeReader(send_queue, ctrl_pipe),
        receiver(cls_pipe, ctrl_pipe),
        sender(send_queue),
    )
    return


# Asyncronously handle requests made to the server.
async def runServer(cls_enum, copter, server):
    ip, port = server.split(':')
    port = int(port)
    print(f"Starting server at {ip}:{port}")
    server = await asyncio.start_server(
        partial(handleClient, cls_enum=cls_enum, copter=copter),
        host=ip,
        port=port
    )
    
    async with server:
        await server.serve_forever()
    return


# Serve client(s) with requested data (see getResponse()).
async def handleClient(reader, writer, cls_enum, copter):
    #MSG_BYTES = 9

    #address = writer.get_extra_info('peername')
    #clients.add(writer)
    print(f"Client ({writer}) added.")

    try:
        while True:
            msg = await reader.readline()
            #if not data:
            #    break
            #msg = json.loads(data.decode())
            #print(f"Server recieved message: {msg}")
            #if msg == '__CLOSE__':
            #    break

            msg = msg.decode().strip()

            response = getResponse(msg, cls_enum, copter)
            response_msg = json.dumps(response).encode() + b'\n'
            writer.write(response_msg)
            await writer.drain()
            #print(f"Server responded to {msg} with: {response}")
        
    except asyncio.CancelledError:
        pass

    finally:
        print("Disconnected.")
        #clients.remove(writer)
        writer.close()
        await writer.wait_closed()
            
    return


# Helper function to retreive the requested message for a client.
def getResponse(msg, cls_enum, copter):
    match msg:
        case 'CLS':
            try:
                # Retrieve classification name.
                response = {'STATUS': 'OK', 'TYPE': 'CLS', 'MSG': Disaster(cls_enum.value).name}
                return response
            except:
                return {'STATUS': 'BAD', 'TYPE': 'CLS', 'MSG': ''}
            
        case 'GPS':
            return {'STATUS': 'OK', 'TYPE': 'CTRL', 'MSG': copter.getLocationGlobal()} #copter.getLocationGlobal()
        
        case 'VEC':
            return {'STATUS': 'OK', 'TYPE': 'CTRL', 'MSG': copter.getDirVector()} #copter.getDirVector()
        
        case '__CLOSE__':
            return {'STATUS': 'OK', 'TYPE': 'EXIT', 'MSG': '__CLOSE__'}


# # Asyncronously handle client messages and subsequent server responses.
# async def client(cls_pipe, ctrl_pipe, clients):

#     #await asyncio.gather(*[handleServer(ip, port) for ip, port in clients])

#     print("Connected to servers.")

#     send_queue = asyncio.Queue()
#     await asyncio.gather(
#         receiver(reader, cls_pipe, ctrl_pipe),
#         sender(writer, send_queue),
#         clsPipeReader(send_queue, cls_pipe),
#         ctrlPipeReader(send_queue, ctrl_pipe)
#     )

#     return

async def handleServer(ip, port):
    RETRY_DELAY = 5
    CONNECTION_ATTEMPTS = 3

    for attempt in range(CONNECTION_ATTEMPTS):
        try:
            reader, writer = await asyncio.open_connection(ip, port)
            connections[(ip, port)] = (reader, writer)
            print(f"Connected to {ip}:{port}.")
            break
        except (ConnectionRefusedError, socket.gaierror, OSError) as error:
            print(f"Attempt #{attempt + 1}. Connection failed: {error}. Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    return

# Asyncronously listen for messages from the classification process.
async def clsPipeReader(send_queue, cls_pipe):

    cls_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(cls_pipe.fileno(), cls_data_available.set)

    while True:
        while not cls_pipe.poll():
            await cls_data_available.wait()
            cls_data_available.clear()
        msg = cls_pipe.recv()
        print(f"msg in clsPipeReader: {msg}")
        if msg == '__CLOSE__':
            break
        await send_queue.put(msg)

    return

# Asyncronously listen for messages from the control process.
async def ctrlPipeReader(send_queue, ctrl_pipe):

    ctrl_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(ctrl_pipe.fileno(), ctrl_data_available.set)

    while True:
        while not ctrl_pipe.poll():
            await ctrl_data_available.wait()
            ctrl_data_available.clear()
        msg = ctrl_pipe.recv()
        if msg == '__CLOSE__':
            break
        await send_queue.put(msg)
    return

# Send a request to the servers (CLS, GPS, VEC, __CLOSE__)
async def sender(send_queue):
    '''Send messages as they become available.'''
    while True:
        msg = await send_queue.get()
        if msg == '__QUIT__':
            break
        
        for (ip, port), (_, writer) in connections.items():
            try:
                writer.write((msg + '\n').encode())
                await writer.drain()
            except Exception as e:
                print(f"{e} error when sending message to {ip}:{port}.")

    writer.close()
    await writer.wait_closed()
    return

# Listen for a response from the servers.
async def receiver(cls_pipe, ctrl_pipe):

    while True:
        msgs = []
        msg_type = ""
        for (ip, port), (reader, _) in connections.items():
            try:
                data = await reader.readline()
                msg_json = json.loads(data.decode())
                msgs.append(msg_json.get('MSG'))
                msg_type = msg_json.get('TYPE')

            except Exception as e:
                print(f"{e} error when sending message to {ip}:{port}.")

        if msg_type == 'CLS':
            cls_pipe.send(msgs)
        elif msg_type == 'CTRL':
            ctrl_pipe.send(msgs)

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


def main():

    args = argParser()
    copter_connection = connectCopter(args.connection)
    copter = drone(copter_connection)
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

    # A name is required for accessing the Airsim camera. Defaults to 'Copter'
    if not args.copter_name:
        copter_name = 'Copter'
    else:
        copter_name = args.copter_name[0]

    # Create classification and control pipes for inter-process network requests.
    par_cls, child_cls = Pipe()
    par_ctrl, child_ctrl = Pipe()

    # Shared value to store latest classification label (Disaster(Enum)) for access by network server.
    cls_enum = Value('i', 5)

    model_path = None
    try:
        model_path = args.model_path[0]
    except:
        model_path = None

    # Handle image gathering and classification.
    cls_process = Process(
        target=classificationYOLO,
        args=(child_cls, cls_enum, copter, args.airsim_ip, model_path, consensus, copter_name,)
    )
    
    # Direct drone path.
    ctrl_thread = Thread(target=droneControl, args=(child_ctrl, copter,))

    processes = [cls_process, ctrl_thread]

    for process in processes:
        print(f"Starting {process} process!")
        process.start()

    # Handle server/client functionality.
    if network_enabled:
        asyncio.run(
            network(par_cls, par_ctrl, cls_enum, copter, args.server[0], clients)
        )

    for process in processes:
        process.join()

    time.sleep(1)
    print("Finished script. Connections closed.")


if __name__ == "__main__":
    main()

