/*
Author: Cameron Lira
File: udp_client.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP client.

Arguments:

*/

#include "practical.h"


int main(int argc, char *argv[]) {

    if (argc < 4 || argc > 5) // Test for correct number of arguments
        DieWithUserMessage("Parameter(s)",
        "<Server Address/Name> <Echo Word> [<Server Port/Service>] <seqNum>");

    char *server = argv[1]; // First arg: server address/name
    char *echoString = argv[2]; // Second arg: word to echo
    int seqNum = atoi(argv[4]);
    // size_t echoStringLen = strlen(echoString);
    // if (echoStringLen > MAXSTRINGLENGTH) // Check input length
    //     DieWithUserMessage(echoString, "string too long");

    // Third arg (optional): server port/service
    char *servPort = argv[3];//(argc == 5) ? argv[3] : "echo";

    // Tell the system what kind(s) of address info we want
    struct addrinfo addrCriteria; // Criteria for address match
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_UNSPEC; // Any address family
    // For the following fields, a zero value means "don't care"
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram sockets
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP protocol

    // Get address(es)
    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(server, servPort, &addrCriteria, &servAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create a datagram/UDP socket
    int sock = socket(servAddr->ai_family, servAddr->ai_socktype,
    servAddr->ai_protocol); // Socket descriptor for client
    if (sock < 0)
        DieWithSystemMessage("socket() failed");

    struct State *curr_state = (struct State*)malloc(sizeof(struct State));
    if (curr_state == NULL) {
        DieWithSystemMessage("malloc memory allocation failed.");
    }

    inet_aton("192.168.12.1", &curr_state->ipv4);
    curr_state->port = 65288;
    curr_state->seqNum = seqNum;

    // Send the string to the server
    ssize_t numBytes = sendto(sock, curr_state, sizeof(struct State), 0,
    servAddr->ai_addr, servAddr->ai_addrlen);
    if (numBytes < 0)
        DieWithSystemMessage("sendto() failed");
    else if (numBytes != sizeof(struct State))
        DieWithUserMessage("sendto() error", "sent unexpected number of bytes");

    // Receive a response

    struct sockaddr_storage fromAddr; // Source address of server
    // Set length of from address structure (in-out parameter)
    socklen_t fromAddrLen = sizeof(fromAddr);
    //char buffer[MAXSTRINGLENGTH + 1]; // I/O buffer

    struct State *rcv_state = (struct State*)malloc(sizeof(struct State));
    if (rcv_state == NULL) {
        DieWithSystemMessage("malloc memory allocation failed.");
    }

    numBytes = recvfrom(sock, rcv_state, sizeof(struct State), 0,
    (struct sockaddr *) &fromAddr, &fromAddrLen);
    if (numBytes < 0)
        DieWithSystemMessage("recvfrom() failed");
    else if (numBytes != sizeof(struct State))
        DieWithUserMessage("recvfrom() error", "received unexpected number of bytes");

    // Verify reception from expected source
    //if (!SockAddrsEqual(servAddr->ai_addr, (struct sockaddr *) &fromAddr))
    //    DieWithUserMessage("recvfrom()", "received a packet from unknown source");

    freeaddrinfo(servAddr);

    //buffer[echoStringLen] = '\0'; // Null-terminate received data
    printf("Received: %d, %d, %ld\n", rcv_state->ipv4.s_addr, rcv_state->port, rcv_state->seqNum); // Print the echoed string
    close(sock);
    exit(0);
    }