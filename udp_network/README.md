# UDP Network

This is a simple networking backend written in C for the purpose of sensor data synchronization across a drone swarm. Currently, GPS and inference data are synchronized. The `udp_airsim_single_cls.py` file is a modified version of the `airsim_single_classification.py` file found in the Airsim code folder. This version uses the UDP networking backend, rather than the TPC, asyncio network model.

### Sources:
AES encryption: [kokke](https://github.com/kokke)

HMAC code: [h5p9sl](https://github.com/h5p9sl) and [gfabiano](https://github.com/gfabiano)