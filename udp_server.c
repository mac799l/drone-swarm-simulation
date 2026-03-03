/*
Author: Cameron Lira
File: udp_server.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP server.

Arguments:
[SERVER PORT] [# CLIENTS] ([CLIENT IP:PORT]s)
*/

#include "practical.h"


void RequestNewData(struct State* rcv_state, int seq_num);
void PrintSocketAddress(const struct sockaddr *address, FILE *stream);
void UpdateState(struct State* curr_state, struct State* new_state);

//u_int8_t NUM_STATES = 4;

enum disasterCls {
    EARTHQUAKE = 0,
    FIRE = 1,
    FLOOD = 2,
    HURRICANE = 3,
    LANDSLIDE = 4,
    NOT_DISASTER = 5,
    OTHER_DISASTER = 6
};

const int MAX_EVENTS = 128;
const int WAIT_SEC = 1;

int main(int argc, char *argv[]){

    /* ------------------ Setup ------------------ */
    const char DELIM = ':';
    int num_clients = stoi(argv[3]);
    bool test = false;
    char *server_port = argv[1];

    if (argc != 3 + num_clients){
        DieWithUserMessage("Parameter(s)", "Incorrect number of arguments");
    } // Test for correct number of arguments

    if (num_clients < 0){
        DieWithUserMessage("Parameter(s)", "# of CLIENTS must be >= 0.");
    }

    if (num_clients == 0){
        num_clients = 4;
        test = true;
    }

    char *ipPorts[num_clients];

    if (!test){ // Read supplied IP:PORTS.
        for (int i = 4; i < 3 + num_clients; i++){
            ipPorts[i] = argv[i];
        }
    }
    else{ //IP:PORT values for testing.
        ipPorts[0] = strdup("192.168.12.1:65288");
        ipPorts[1] = strdup("192.168.12.2:65288");
        ipPorts[2] = strdup("192.168.12.3:65288");
        ipPorts[3] = strdup("192.168.12.4:65288");
    }

    int num_states = num_clients + 1;

    char *ips[num_states];
    char *ports[num_states];

    // Split up IP:PORTS.
    for (int i = 0; i < num_states; i++) {
        ips[i] = strtok(ipPorts[i], &DELIM);
        ports[i] = strtok(NULL, "\n");
    }

    for (int i = 0; i < num_states; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ips[i], ports[i]);
    }
    
    // Create state vector.
    struct State *stateVector[num_states];
    for (int i = 0; i < num_states; i++) {
        
        // Allocate a new state.
        struct State* state = (struct State*)malloc(sizeof(struct State));
        if (state == NULL) {
            DieWithSystemMessage("malloc memory allocation failed.");
        }
        struct GPS *gps = (struct GPS*)malloc(sizeof(struct GPS));
        gps->longitude = 0.0;
        gps->latitude = 0.0;
        gps->altitude = 0.0;
        time_t now = time(NULL);
        
        // Load default state into state vector.
        inet_pton(AF_INET, ipPorts[i], &state->ipv4);
        state->port = atoi(ports[i]);
        state->gpsState = gps;
        state->seqNum = 0;
        state->timestamp = now;//gmtime(now);
        state->classification = NOT_DISASTER;
        state->isValid = false;
        // Set vector.
        stateVector[i] = state;
    } 


    /* ------------------ Server Socket ------------------ */

    // Construct the server address structure
    struct addrinfo svrAddrCriteria; // Criteria for address
    memset(&svrAddrCriteria, 0, sizeof(svrAddrCriteria)); // Zero out structure
    svrAddrCriteria.ai_family = AF_UNSPEC; // Any address family
    svrAddrCriteria.ai_flags = AI_PASSIVE; // Accept on any address/port
    svrAddrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram socket
    svrAddrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP socket

    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(NULL, server_port, &svrAddrCriteria, &servAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create socket for incoming connections
    int svr_sock_fd = socket(servAddr->ai_family, servAddr->ai_socktype,
    servAddr->ai_protocol);
    if (svr_sock_fd < 0)
        DieWithSystemMessage("socket() failed");

    // Bind to the local address
    if (bind(svr_sock_fd, servAddr->ai_addr, servAddr->ai_addrlen) < 0)
        DieWithSystemMessage("bind() failed");

    // Free address list allocated by getaddrinfo()
    //freeaddrinfo(servAddr);


    /* ------------------ Client Socket ------------------ */

    // Tell the system what kind(s) of address info we want
    struct addrinfo clientAddrCriteria; // Criteria for address match
    memset(&clientAddrCriteria, 0, sizeof(clientAddrCriteria)); // Zero out structure
    clientAddrCriteria.ai_family = AF_UNSPEC; // Any address family

    // For the following fields, a zero value means "don't care"
    clientAddrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram sockets
    clientAddrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP protocol

    // Get address(es)
    struct addrinfo *clientServAddr; // List of server addresses
    rtnVal = getaddrinfo(server, server_port, &clientAddrCriteria, &clientServAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create a datagram/UDP socket
    int client_sock_fd = socket(clientServAddr->ai_family, clientServAddr->ai_socktype,
    servAddr->ai_protocol); // Socket descriptor for client
    if (client_sock_fd < 0)
        DieWithSystemMessage("socket() failed");

    //freeaddrinfo(servAddr);


    /* ------------------ Epoll Setup ------------------ */
    int epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        DieWithSystemMessage("epoll_create1 failed");
    }

    struct epoll_event ep_event = { .events = EPOLLIN, .data.fd = svr_sock_fd };
    epoll_ctl(epoll_fd, EPOLL_CTL_ADD, svr_sock_fd, &ep_event);
    ep_event.events = EPOLLIN;
    ep_event.data.fd = client_sock_fd;
    epoll_ctl(epoll_fd, EPOLL_CTL_ADD, client_sock_fd, &ep_event);


    /* ------------------ Run server/client ------------------ */
    struct epoll_event events[MAX_EVENTS];
    int timeout = WAIT_SEC * 1000;
    while(true){
        int nfds = epoll_wait(epoll_fd, events, MAX_EVENTS, timeout);

        for (int i = 0; i < nfds; i++){
            int fd = events[i].data.fd;

            if (fd == svr_sock_fd && (events[i].events & EPOLLIN)) {
                struct State *rcv_state = (struct State *)malloc(sizeof(struct State));
                if (rcv_state == NULL) {
                    DieWithSystemMessage("malloc memory allocation failed.");
                }
                struct sockaddr_storage clntAddr; // Client address
                // Set Length of client address structure (in-out parameter)
                socklen_t clntAddrLen = sizeof(clntAddr);

                // Block until receive message from a client
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
                    if (curr_state->ipv4.s_addr == rcv_state->ipv4.s_addr && curr_state->seqNum < rcv_state->seqNum) {
                        RequestNewData(rcv_state, curr_state->seqNum);
                        UpdateState(curr_state, rcv_state);
                        break;
                        //curr_state = rcv_state;
                    }
                }
            }

            if (fd == client_sock_fd) {
                // IN
                if (events[i].events & EPOLLIN) {
                    //HANDLE
                }

                if (events[i].events & EPOLLOUT) {
                    // HANDLE
                }
            }
        }
    }

    return 0;
}


int UdpServer(char *port, int num_states) {

    char *service = port;

    // Create state vector.
    struct State *stateVector[num_states];
    for (int i = 0; i < num_states; i++) {
        
        // Allocate a new state.
        struct State* state = (struct State*)malloc(sizeof(struct State));
        if (state == NULL) {
            DieWithSystemMessage("malloc memory allocation failed.");
        }
        struct GPS *gps = (struct GPS*)malloc(sizeof(struct GPS));
        gps->longitude = 0.0;
        gps->latitude = 0.0;
        gps->altitude = 0.0;
        time_t now = time(NULL);
        
        // Load default state into state vector.
        inet_pton(AF_INET, ipPorts[i], &state->ipv4);
        state->port = atoi(port[i]);
        state->gpsState = gps;
        state->seqNum = 0;
        state->timestamp = now;//gmtime(now);
        state->classification = NOT_DISASTER;
        state->isValid = false;
        // Set vector.
        stateVector[i] = state;
    }    

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
            if (curr_state->ipv4.s_addr == rcv_state->ipv4.s_addr && curr_state->seqNum < rcv_state->seqNum) {
                RequestNewData(rcv_state, curr_state->seqNum);
                UpdateState(curr_state, rcv_state);
                break;
                //curr_state = rcv_state;
            }
        }
    }
    // NOT REACHED
}


int UdpClient(int argc, char *argv[]) {

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



void RequestNewData(struct State* rcv_state, int seq_num) {
    printf("NEWER DATA DETECTED. SETTING SEQ NUM: %d to %ld\n", seq_num, rcv_state->seqNum);
    //rcv_state->seq_num = seq_num
}

void UpdateState(struct State* curr_state, struct State* new_state){
    struct State* old_state = curr_state;
    curr_state = new_state;
    free(old_state);
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

// Generates a random state (simulates local state vector update).
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