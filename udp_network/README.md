# UDP Network

This is a simple networking backend written in C for the purpose of sensor data synchronization across an Airsim drone swarm. Currently, GPS and inference data are synchronized. The `udp_airsim_single_cls.py` file is a modified version of the `airsim_single_classification.py` file found in the Airsim `code` folder. This version uses UDP the new networking backend, rather than the TCP, asyncio network model.

> The Python code files will be reincorporated with the main Airsim folder in time. The Python files are copied here so changes can be made without breaking the other Python code - particularly shared files such as `droneclass_dk.py`.

### Sources:
AES encryption: [kokke](https://github.com/kokke)

HMAC code: [h5p9sl](https://github.com/h5p9sl) and [gfabiano](https://github.com/gfabiano)

JSON library: [DaveGamble](https://github.com/DaveGamble)
