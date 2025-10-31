"""
    Filename: single_uav_classification.py
    Author: Cameron Lira
    Updated: 2025-08-13
    Project: Drone Swarm Control Using SITL and Gazebo

    Description:
    Commands a connected drone to follow a preset path defined in the control function.
    It also performs classification using a Gstreamer udp video source from the Ardupilot Gazebo Gstreamer plugin using YOLO and Opencv.

    NOTE: the script is currently designed to perform YOLO classification using a YOLO model trained on the MEDIC disaster dataset.
    Minor modifications would be needed to perform other tasks.

    Arguments:
    --connect PROTOCOL:IP:PORT (provide the connection information, otherwise defaults to a serial connection).
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

# Detected classes for use by a YOLO model trained on the MEDIC dataset.
class Disaster(Enum):
    EARTHQUAKE = 0
    FIRE = 1
    FLOOD = 2
    HURRICANE = 3
    LANDSLIDE = 4
    NOT_DISASTER = 5
    OTHER_DISASTER = 6

# Global Constants
AIRSIM_HOST_IP = '172.24.112.1'
SERVER_IP_ADDRESS = '127.0.0.1'
SERVER_PORT = 65288

CLIENT_IP_ADDRESS = '127.0.0.1'
CLIENT_PORT = 65289

YOLO_MODEL_PATH = "/home/cameron/yolo_v11_custom/yolo_dataset/trained_models/best.pt"
#frame_data = []
#copter = None

#clients = []

# Connect to the drone.
def connectCopter():

    connection = argParser()
    # Default to a physical connection (i.e. RaspberryPi serial connection).
    if not connection:
        connection = "/dev/serial0"
        print("No connection argument! Attempting to connect over serial.")

    print(connection)

    vehicle = connect(connection, wait_ready=True)
    return vehicle


# Connected to camera stream.
def connectCamera():

    client = airsim.MultirotorClient(ip=AIRSIM_HOST_IP)
    client.confirmConnection()
    client.enableApiControl(True)

    return client


# Perform classification on the camera stream.
def classificationYOLO(pipe, cls_enum, copter):

    client = connectCamera()
    print("Camera connected.")

    DETECTION_THRESHOLD = 0.5
    model = YOLO(YOLO_MODEL_PATH)
    frame_data = []
    frame_data.append([0,"NOT_DISASTER", 0, [0,0,0]])
    time.sleep(5)
    while True:
        #time.sleep(1)
        frame = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name="Copter0")
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
            cls_enum.value = 5
        
        # Get consensus from other drones.
        #consensus_reached, enum_name = swarm.consensus(enum_name)
        pipe.send("CLS")
        drone_2_cls = pipe.recv()

        #drone_2_cls = Disaster(drone_2_cls).name
        
        #print(f"Drone_2_cls: {drone_2_cls}.")

        consensus_reached = False
        if enum_name == drone_2_cls and enum_name != "NOT_DISASTER":
            consensus_reached = True

        if consensus_reached and confidence > DETECTION_THRESHOLD:
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
            pipe.send("__CLOSE__")
            break

    cv.destroyAllWindows()

    return


def droneControl(pipe, copter):



    print(f"Copter: {copter}")

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(100)
    
    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 5, velocity_z = 0, duration = 15, pipe=pipe)
    time.sleep(1)

    copter.send_global_ned_velocity(velocity_x = -15, velocity_y = -5, velocity_z = 0, duration = 15, pipe=pipe)

    #copter.go_to(copter.getHome())
    time.sleep(1)
    
    time.sleep(10)
    copter.land()

    return

# Handle server and client coroutines.
async def network(cls_pipe, ctrl_pipe, cls_enum, copter):
    await asyncio.gather(
        server(cls_enum, copter),
        client(cls_pipe, ctrl_pipe)
    )
    return

# Asyncronously handle server and client requests.
async def server(cls_enum, copter):
    print(f"Starting server at {SERVER_IP_ADDRESS}:{SERVER_PORT}")
    server = await asyncio.start_server(
        partial(handleClient, cls_enum = cls_enum, copter=copter),
        host=SERVER_IP_ADDRESS,
        port=SERVER_PORT
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
            #if msg == "__CLOSE__":
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


def getResponse(msg, cls_enum, copter):
    match msg:
        case "CLS":
            try:
                # Retrieve classification name.
                response = {"STATUS": "OK", "TYPE": "CLS", "MSG": Disaster(cls_enum.value).name}
                return response
            except:
                return {"STATUS": "BAD", "TYPE": "CLS", "MSG": ""}
            
        case "GPS":
            return {"STATUS": "OK", "TYPE": "CTRL", "MSG": copter.getLocationGlobal()} #copter.getLocationGlobal()
        
        case "VEC":
            return {"STATUS": "OK", "TYPE": "CTRL", "MSG": copter.getDirVector()} #copter.getDirVector()
        
        case "__CLOSE__":
            return {"STATUS": "OK", "TYPE": "EXIT", "MSG": "__CLOSE__"}

# Asyncronously handle client messages and subsequent server responses.
async def client(cls_pipe, ctrl_pipe):
    RETRY_DELAY = 5
    while True:
        try:
            reader, writer = await asyncio.open_connection(CLIENT_IP_ADDRESS, CLIENT_PORT)
            print("Connected!")
            break
        except (ConnectionRefusedError, socket.gaierror, OSError) as error:
            print(f"Connection failed: {error}. Retrying in {RETRY_DELAY} secs...")
            await asyncio.sleep(RETRY_DELAY)

    print("Connected to server.")

    send_queue = asyncio.Queue()
    await asyncio.gather(
        receiver(reader, cls_pipe, ctrl_pipe),
        sender(writer, send_queue),
        cls_pipe_reader(send_queue, cls_pipe),
        ctrl_pipe_reader(send_queue, ctrl_pipe)
        #background_data_source(cls_pipe, ctrl_pipe, send_queue)
    )

    return

'''
async def background_data_source(cls_pipe, ctrl_pipe, send_queue):
    # TODO: Handle CTRL pipe.
    cls_data_available = asyncio.Event()
    #ctrl_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(cls_pipe.fileno(), cls_data_available.set)
    #asyncio.get_event_loop().add_reader(ctrl_pipe.fileno(), ctrl_data_available.set)
    while True:
        while not cls_pipe.poll():
            await cls_data_available.wait()
            cls_data_available.clear()
        msg = cls_pipe.recv()
        if msg == "__CLOSE__":
            break
        send_queue.put(msg)
'''
# Asyncronously listen for messages from the classification process.
async def cls_pipe_reader(send_queue, cls_pipe):

    cls_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(cls_pipe.fileno(), cls_data_available.set)

    while True:
        while not cls_pipe.poll():
            await cls_data_available.wait()
            cls_data_available.clear()
        msg = cls_pipe.recv()
        if msg == "__CLOSE__":
            break
        await send_queue.put(msg)

    return

# Asyncronously listen for messages from the control process.
async def ctrl_pipe_reader(send_queue, ctrl_pipe):

    ctrl_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(ctrl_pipe.fileno(), ctrl_data_available.set)

    while True:
        while not ctrl_pipe.poll():
            await ctrl_data_available.wait()
            ctrl_data_available.clear()
        msg = ctrl_pipe.recv()
        if msg == "__CLOSE__":
            break
        await send_queue.put(msg)
    return

# Send a request to the server (CLS, GPS, VEC, __CLOSE__)
async def sender(writer, send_queue):
    """Send messages as they become available."""
    while True:
        msg = await send_queue.get()
        if msg == "__QUIT__":
            break
        
        writer.write((msg + '\n').encode())
        await writer.drain()
        #print(f"Message sent: {msg}")
    writer.close()
    await writer.wait_closed()
    return

# Listen for a response from the server.
async def receiver(reader, cls_pipe, ctrl_pipe):

    while True:
        data = await reader.readline()
        
        msg_json = json.loads(data.decode())

        #if not msg or msg == "__CLOSE__":
        #    print("Server closed connection.")
        #    break

        #print(f"Recieved response from server: {msg}")
        
        #if msg_json.get("STATUS") != "OK":
        #    break
        
        msg = msg_json.get("MSG")

        msg_type = msg_json.get("TYPE")
        if msg_type == "CLS":
            cls_pipe.send(msg)
        elif msg_type == "CTRL":
            ctrl_pipe.send(msg)

    return


def argParser():

    parser = argparse.ArgumentParser(description='commands')
    parser.add_argument('--connect')
    args = parser.parse_args()
    connection = args.connect
    
    return connection


def main():

    copter_connection = connectCopter()
    copter = drone(copter_connection)
    print("Copter connected.")

    # Create pipes for process network communication.
    par_cls, child_cls = Pipe()
    par_ctrl, child_ctrl = Pipe()

    cls_enum = Value('i', 5)

    # Process 1: handle classification
    classification_p = Process(target=classificationYOLO, args=(child_cls, cls_enum, copter, ))

    # Process 2: handle drone commands
    #control_p = Process(target=droneControl, args=(child_ctrl,))
    
    control_thread = Thread(target=droneControl, args=(child_ctrl, copter,))

    # Process 3: handle server/client communication
    #server_p = Process(target=droneServer, args=(par_cls, par_cont,))
    #processes.append(server_p)

    processes = [classification_p, control_thread]

    for process in processes:
        print(f"Starting {process} process!")
        process.start()

    #asyncio.run(server())
    asyncio.run(network(par_cls, par_ctrl, cls_enum, copter))

    for process in processes:
        process.join()




    '''
    copter_connection = connectCopter()
    client = connectCamera()

    copter = drone(copter_connection)

    drone_operations = [droneControl,classificationYOLO]
    arguments = [[copter,], [client, copter]]
    threads = []

    for i, arg in enumerate(arguments):
        thread = threading.Thread(target=drone_operations[i], args=arg)
        threads.append(thread)

    for thread in threads:
        thread.start()

    asyncio.run(server)

    for thread in threads:
        thread.join()

    '''

    time.sleep(1)
    print("Finished script. Closing connections.")

    # Close connections.
    #copter_connection.close()


if __name__ == "__main__":
    main()
