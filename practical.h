/*
Author: Cameron Lira
File: practical.h
Project: CS395 UDP Broadcast Project

File Description:
    Defines helper functions and constants for udp_server.c

*/

#pragma once

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <string.h>
#include <netdb.h>
#include <stdbool.h>
#include <time.h>
#include "sha256.h"
#include "hmac_sha256.h"

extern int MAXSTRINGLENGTH;
extern int IPV4_ADDRESS_LEN;
extern int PORT_LEN;

struct GPS {
    float latitude;
    float longitude;
    float altitude;
};

struct State {
    struct GPS gpsState;
    u_int64_t seqNum;
    struct in_addr ipv4;
    time_t timestamp; // TODO: change to long long before 2038.
    u_int16_t port;
    u_int8_t classification;
    bool isValid;
};

struct packet {
    struct State state; // Encrypted state.
    u_int8_t hmac[SHA256_HASH_SIZE];
    u_int8_t iv[16]; // Send IV in the clear.
    u_int8_t type; // Packet type.
};

void DieWithUserMessage(const char *msg, const char *detail);

void DieWithSystemMessage(const char *msg);

//void PrintSocketAddress(const struct sockaddr *address, FILE *stream);