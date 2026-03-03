/*
Author: Cameron Lira
File: udp_client.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP client.

Arguments:

*/

#include "practical.h"

// Better random state generator
// Returns 0 on success, -1 on failure (e.g. allocation failed)
int GenerateRandomState(struct State *state)
{
    static uint64_t sequence = 0;
    static bool     initialized = false;

    if (!initialized) {
        srand((unsigned int)time(NULL) ^ (unsigned int)clock());
        initialized = true;
    }

    if (!state || !state->gpsState) {
        return -1;
    }

    // Sequence number (monotonically increasing)
    state->seqNum = ++sequence;

    // Realistic-ish timestamp
    state->timestamp = time(NULL);

    // Random but plausible classification (0–4 for example)
    state->classification = (uint8_t)(rand() % 7);

    // Random validity (70% chance valid)
    state->isValid = (rand() % 10) < 7;

    // Fake IPv4 address (mostly in 10.0.0.0/8 private range + some public-looking)
    uint32_t ip_pattern[] = {
        0x0A000001,     // 10.0.0.1
        0x0A14AB01,     // 10.20.171.1
        0xAC100001,     // 172.16.0.1
        0xC0A80101,     // 192.168.1.1
        0x08080808,     // 8.8.8.8 (public DNS)
        0x01010101,     // 1.1.1.1 (Cloudflare)
        0x2F000001      // 47.0.0.1
    };
    state->ipv4.s_addr = ip_pattern[rand() % (sizeof(ip_pattern)/sizeof(ip_pattern[0]))];

    // Random port (mostly ephemeral range)
    state->port = 1024 + (rand() % (65535 - 1024 + 1));

    // Realistic-ish GPS coordinates
    struct GPS *gps = state->gpsState;

    // Latitude: -90 to +90
    gps->latitude  = -90.0f + (float)rand() / RAND_MAX * 180.0f;

    // Longitude: -180 to +180
    gps->longitude = -180.0f + (float)rand() / RAND_MAX * 360.0f;

    // Altitude: sea level to ~12 km (aircraft), sometimes negative (test)
    gps->altitude  = -500.0f + (float)rand() / RAND_MAX * 13000.0f;

    return 0;
}

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
    char ip[24];
    inet_ntop(AF_INET, &rcv_state->ipv4.s_addr, ip, 24); 
    printf("Received: %s, %d, %ld\n", ip, rcv_state->port, rcv_state->seqNum); // Print the echoed string
    close(sock);
    exit(0);
    }