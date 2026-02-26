/*
Author: Cameron Lira
File: practical.h
Project: CS395 UDP Broadcast Project

File Description:
    Defines helper functions and constants for udp_server.c and udp_client.c

*/

#ifndef PRACTICAL_H
#define PRACTICAL_H

#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <stdbool.h>
#include <time.h>

extern int MAXSTRINGLENGTH;
extern int IPV4_ADDRESS_LEN;
extern int PORT_LEN;

struct GPS {
    float latitude;
    float longitude;
    float altitude;
} gps;

struct State {
    struct GPS *gpsState;
    u_int64_t seqNum;
    struct in_addr ipv4;
    time_t timestamp; // TODO: change to long long before 2038.
    u_int16_t port;
    u_int8_t classification;
    bool isValid;
} state_vector;

void DieWithUserMessage(const char *msg, const char *detail);

void DieWithSystemMessage(const char *msg);

//void PrintSocketAddress(const struct sockaddr *address, FILE *stream);

#endif