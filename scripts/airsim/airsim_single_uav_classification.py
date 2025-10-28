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
from drone_network import swarm
import asyncio
from multiprocessing import Process, Value, Pipe
from functools import partial

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
AIRSIM_HOST_IP = ""
SERVER_IP_ADDRESS = ""
SERVER_PORT = ""

CLIENT_IP_ADDRESS = ""
CLIENT_PORT = ""

frame_data = []
copter = None

clients = []

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
def classificationYOLO(client, copter, pipe, cls_enum):

    DETECTION_THRESHOLD = 0.5
    model = YOLO("/home/cameron/yolo_v11_custom/yolo_dataset/trained_models/best.pt")
    #frame_data = []
    frame_data.append([0,"NOT_DISASTER", 0, [0,0,0]])

    while True:

        frame = client.simGetImage("0", airsim.ImageType.Scene)
        nparr = np.frombuffer(frame, np.uint8)
        img = cv.imdecode(nparr, cv.IMREAD_COLOR)

        results = model.predict(source = img, verbose = True)
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
        drone_2_cls = pipe.rcv()
        
        consensus_reached = False
        if enum_name == drone_2_cls and enum_name != "NOT_DISASTER":
            consensus_reached = True

        if consensus_reached and confidence > DETECTION_THRESHOLD:
            print("Detected class:", enum_name ,"-- Probability:",'{0:.2f}'.format(confidence.item()), " -- GPS:", location)
            if enum_name != frame_data[-1][1]:
                frame_data.append([frame, enum_name, confidence, location])
            elif frame_data[-1][2] < confidence:
                frame_data.pop()
                frame_data.append([frame, enum_name, confidence, location])

        # Press 'q' from the camera window to stop classification.
        if cv.waitKey(1) == ord('q'):
            break

    cv.destroyAllWindows()

    return


def droneControl(copter, pipe):

    AIRSPEED, GROUNDSPEED = 8, 8
    copter.setHome()

    copter.printInfo()
    copter.setSpeed(AIRSPEED,GROUNDSPEED)

    time.sleep(1)
    copter.takeoff(50)

    time.sleep(1)
    print("Altitude: ", copter.getAltGlobal(), "meters.")

    copter.send_global_ned_velocity(velocity_x = 15, velocity_y = 0, velocity_z = 0, duration = 15, pipe=pipe)
    time.sleep(5)

    copter.go_to(copter.getHome())
    time.sleep(1)
    copter.land()

    return


async def network(cls_pipe, ctrl_pipe, cls_enum):
    await asyncio.gather(
        server(cls_enum),
        client(cls_pipe, ctrl_pipe)
    )
    return


async def server(cls_enum):

    server = await asyncio.start_server(
        partial(handleClient, cls_enum = cls_enum),
        host=SERVER_IP_ADDRESS,
        port=SERVER_PORT
    )
    
    async with server:
        await server.serve_forever
    return


async def handleClient(reader, writer, cls_enum):
    MSG_BYTES = 3

    address = writer.get_extra_info('peername')
    clients.add(writer)
    print(f"Client ({writer}) added.")

    try:
        while True:
            data = await reader.read(MSG_BYTES)
            if not data:
                break
            msg = data.decode().strip()
            response = getResponse(msg, cls_enum)

            writer.write(response.encode())
            await writer.drain()
        
    except asyncio.CancelledError:
        pass

    finally:
        print("Disconnected.")
        clients.remove(writer)
        writer.close()
        await writer.wait_closed()
            
    return


def getResponse(msg, cls_enum):
    match msg:
        case "CLS":
            try:
                # TODO: Fix method to use label name, not saved label.
                # Retrieve classification name.
                response = cls_enum.value
                return response
            except:
                return "NONE"
            
        case "GPS":
            return copter.getLocationGlobal()
        
        case "VEC":
            return copter.getDirVector()


async def client(cls_pipe, ctrl_pipe):

    reader, writer = await asyncio.open_connection(CLIENT_IP_ADDRESS, CLIENT_PORT)
    print("Connected to server.")

    send_queue = asyncio.Queue()
    await asyncio.gather(
        receiver(reader),
        sender(writer, send_queue),
        cls_pipe_reader(send_queue, cls_pipe),
        ctrl_pipe_reader(send_queue, ctrl_pipe)
        #background_data_source(cls_pipe, ctrl_pipe, send_queue)
    )

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
        msg = cls_pipe.rcv()
        if msg == "__CLOSE__":
            break
        send_queue.put(msg)
'''

async def cls_pipe_reader(send_queue, cls_pipe):

    cls_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(cls_pipe.fileno(), cls_data_available.set)

    while True:
        while not cls_pipe.poll():
            await cls_data_available.wait()
            cls_data_available.clear()
        msg = cls_pipe.rcv()
        if msg == "__CLOSE__":
            break
        send_queue.put(msg)


async def ctrl_pipe_reader(send_queue, ctrl_pipe):

    ctrl_data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(ctrl_pipe.fileno(), ctrl_data_available.set)

    while True:
        while not ctrl_pipe.poll():
            await ctrl_data_available.wait()
            ctrl_data_available.clear()
        msg = ctrl_pipe.rcv()
        if msg == "__CLOSE__":
            break
        send_queue.put(msg)

async def sender(writer, send_queue):
    """Send messages as they become available."""
    while True:
        msg = await send_queue.get()
        if msg == "__QUIT__":
            break
        writer.write(msg.encode())
        await writer.drain()
    writer.close()
    await writer.wait_closed()


async def receiver(reader, cls_pipe, ctrl_pipe):
    """Listen for messages from the server."""
    while True:
        data = await reader.read(1024)
        if not data:
            print("Server closed connection.")
            break
        
        if isinstance(data, str):
            cls_pipe.send(data)
        else:
            ctrl_pipe.send(data)
        
        '''
        if data in Disaster.__members__:
            cls_pipe.send(data)
        else:
            ctrl_pipe.send(data)
        '''

    return


def argParser():

    parser = argparse.ArgumentParser(description='commands')
    parser.add_argument('--connect')
    args = parser.parse_args()
    connection = args.connect
    
    return connection


def main():

    copter_connection = connectCopter()
    airsim_camera = connectCamera()

    copter = drone(copter_connection)

    # Create pipes
    par_cls, child_cls = Pipe()
    par_ctrl, child_ctrl = Pipe()

    cls_enum = Value('i', 5)

    # Process 1: handle classification
    classification_p = Process(target=classificationYOLO, args=(airsim_camera, copter, child_cls, cls_enum,))

    # Process 2: handle drone commands
    control_p = Process(target=droneControl, args=(copter, child_ctrl,))
    
    # Process 3: handle server/client communication
    #server_p = Process(target=droneServer, args=(par_cls, par_cont,))
    #processes.append(server_p)

    processes = [classification_p, control_p]

    for process in processes:
        process.start()

    #asyncio.run(server())
    asyncio.run(network(par_cls, par_ctrl, cls_enum))

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
    copter_connection.close()


if __name__ == "__main__":
    main()
