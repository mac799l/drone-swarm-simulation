/*
Author: Cameron Lira
File: udp_server.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP server.

Arguments:

*/

#include "practical.h"


void RequestNewData(struct State* rcv_state, int seq_num);

// Args: server port/service, num_clients, client(s) IP/PORTS.
void PrintSocketAddress(const struct sockaddr *address, FILE *stream);

u_int8_t NUM_STATES = 4;

int main(int argc, char *argv[]) {

    const char DELIM = ':';

    if (argc != 2) // Test for correct number of arguments
        DieWithUserMessage("Parameter(s)", "<Server Port/Service>");

    // Example provided IP:PORT values. Will be a CL argument.
    char *ipPorts[NUM_STATES];
    ipPorts[0] = strdup("192.168.12.1:65288");
    ipPorts[1] = strdup("192.168.12.2:65288");
    ipPorts[2] = strdup("192.168.12.3:65288");
    ipPorts[3] = strdup("192.168.12.4:65288");

    char *ip[NUM_STATES];
    char *port[NUM_STATES];

    char *tokens;
    for (int i = 0; i < NUM_STATES; i++) {
        ip[i] = strtok(ipPorts[i], &DELIM);
        port[i] = strtok(NULL, "\n");
    }

    for (int i = 0; i < NUM_STATES; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ip[i], port[i]);
    }


    /*
    struct State {
    struct GPS gpsState;
    u_int64_t seqNum;
    struct in_addr ipv4;
    time_t timestamp; // TODO: change to long long before 2038.
    u_int16_t port;
    u_int8_t classification;
    bool isValid;
} state_vector;

    */

    // Create state vector.
    struct State *stateVector[NUM_STATES];
    for (int i = 0; i < NUM_STATES; i++) {
        // Allocate a new state.
        struct State* state = (struct State*)malloc(sizeof(struct State));
        if (state == NULL) {
            DieWithSystemMessage("malloc memory allocation failed.");
        }
        // Initial sequence number.
        state->seqNum = 0;
        // Load IP:PORT data into state vector.
        inet_aton(ipPorts[i], &state->ipv4);
        state->port = port[i];
        stateVector[i] = state;
    }    

    char *service = argv[1]; // First arg: local port/service

    // Construct the server address structure
    struct addrinfo addrCriteria; // Criteria for address
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_UNSPEC; // Any address family
    addrCriteria.ai_flags = AI_PASSIVE; // Accept on any address/port
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram socket
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP socket

    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(NULL, service, &addrCriteria, &servAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create socket for incoming connections
    int sock = socket(servAddr->ai_family, servAddr->ai_socktype,
    servAddr->ai_protocol);
    if (sock < 0)
        DieWithSystemMessage("socket() failed");

    // Bind to the local address
    if (bind(sock, servAddr->ai_addr, servAddr->ai_addrlen) < 0)
        DieWithSystemMessage("bind() failed");

    // Free address list allocated by getaddrinfo()
    freeaddrinfo(servAddr);

    for (;;) { // Run forever
        struct State *rcv_state = (struct State *)malloc(sizeof(struct State));
        if (rcv_state == NULL) {
            DieWithSystemMessage("malloc memory allocation failed.");
        }
        struct sockaddr_storage clntAddr; // Client address
        // Set Length of client address structure (in-out parameter)
        socklen_t clntAddrLen = sizeof(clntAddr);

        // Block until receive message from a client
        //char buffer[MAXSTRINGLENGTH]; // I/O buffer
        // Size of received message
        ssize_t numBytesRcvd = recvfrom(sock, rcv_state, sizeof(struct State), 0,
            (struct sockaddr *) &clntAddr, &clntAddrLen);
        if (numBytesRcvd < 0)
            DieWithSystemMessage("recvfrom() failed");

        fputs("Handling client ", stdout);
        PrintSocketAddress((struct sockaddr *) &clntAddr, stdout);
        fputc('\n', stdout);

        // Send received datagram back to the client
        ssize_t numBytesSent = sendto(sock, rcv_state, sizeof(struct State), 0,
        (struct sockaddr *) &clntAddr, sizeof(clntAddr));
        if (numBytesSent < 0)
            DieWithSystemMessage("sendto() failed)");
        else if (numBytesSent != numBytesRcvd)
            DieWithUserMessage("sendto()", "sent unexpected number of bytes");

        for (int i = 0; i < NUM_STATES; i++) {
            printf("stateVector %d\n", i);
            struct State *curr_state = stateVector[i];
            //if (curr_state->ipv4 == rcv_state->ipv4 && curr_state->seqNum < rcv_state->seqNum) {
            //    RequestNewData(rcv_state, curr_state->seqNum);
            //}
        }
    }
    // NOT REACHED
}

void RequestNewData(struct State* rcv_state, int seq_num) {
    printf("NEWER DATA DETECTED. SETTING SEQ NUM: %d to %ld", seq_num, rcv_state->seqNum);
    //rcv_state->seq_num = seq_num
}


void PrintSocketAddress(const struct sockaddr *address, FILE *stream) {
    // Test for address and stream
    if (address == NULL || stream == NULL)
        return;
    void *numericAddress; // Pointer to binary address
    // Buffer to contain result (IPv6 sufficient to hold IPv4)
    char addrBuffer[INET6_ADDRSTRLEN];
    in_port_t port; // Port to print
    // Set pointer to address based on address family
    switch (address->sa_family) {
        case AF_INET:
            numericAddress = &((struct sockaddr_in *) address)->sin_addr;
            port = ntohs(((struct sockaddr_in *) address)->sin_port);
            break;
        case AF_INET6:
            numericAddress = &((struct sockaddr_in6 *) address)->sin6_addr;
            port = ntohs(((struct sockaddr_in6 *) address)->sin6_port);
            break;
        default:
            fputs("[unknown type]", stream); // Unhandled type
            return;
    }
    // Convert binary to printable address
    if (inet_ntop(address->sa_family, numericAddress, addrBuffer, sizeof(addrBuffer)) == NULL)
        fputs("[invalid address]", stream); // Unable to convert
    else {
    fprintf(stream, "%s", addrBuffer);
    if (port != 0) // Zero not valid in any socket addr
    fprintf(stream, "-%u", port);
    }
}