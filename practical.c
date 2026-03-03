/*
Author: Cameron Lira
File: practical.c
Project: CS395 UDP Broadcast Project

File Description:
    Defines helper functions and constants for udp_server.c and udp_client.c

*/
#include "practical.h"

int MAXSTRINGLENGTH = 64;
int IPV4_ADDRESS_LEN = 16;
int PORT_LEN = 6;


void DieWithUserMessage(const char *msg, const char *detail){
    fputs(msg, stderr);
    fputs(": ", stderr);
    fputs(detail, stderr);
    fputc('\n', stderr);
    exit(1);
}

void DieWithSystemMessage(const char *msg){
    perror(msg);
    exit(1);
}