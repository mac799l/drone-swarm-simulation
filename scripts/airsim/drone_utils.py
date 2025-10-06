import math

def gpsDistance(gps_1, gps_2):
    EARTH_RADIUS_MILES = 3963
    lat_1, long_1 = gps_1[0], gps_1[1]
    lat_2, long_2 = gps_2[0], gps_2[1]

    # Compute distance using Haversine distance formula.
    lat_sin = math.sin( (lat_2 - lat_1) / 2 ) ** 2
    long_sin = math.sin( (long_2 - long_1) / 2 ) ** 2
    distance = (lat_sin + math.cos(lat_1) * math.cos(lat_2) * long_sin)
    distance = math.sqrt(distance)
    distance = math.asin(distance)
    distance = 2*EARTH_RADIUS_MILES * distance

    return distance