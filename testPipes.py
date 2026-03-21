import time
import subprocess
import argparse
import json



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
    msg_json = {"ip": state.ip, "cls": state.gps, "gps": state.gps}
    msg_json = json.dumps(msg_json).encode() + b'\n'
    return msg_json

async def listenServerPipe(udp_server):
    msg = udp_server.stdout.read()


def main():

    args = argParser()

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

    num_clients = len(clients)
    # Handle server/client functionality.

    udp_server = subprocess.Popen(["/home/cameron/cs395_udpbroadcast/udp_server", 
                        str(args.server[0]), 
                        str(num_clients),
                        str(*clients)], 
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE)

    # for process in processes:
    #     process.join()
    while True:
        udp_server.stdin.write(b"Hello from Python!\n")
        udp_server.stdin.flush()
        print(udp_server.stdout.readline().decode())
        #udp_server.stdout.readline()
        time.sleep(1)



if __name__ == "__main__":
    main()