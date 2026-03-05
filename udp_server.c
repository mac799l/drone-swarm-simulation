/*
Author: Cameron Lira
File: udp_server.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP server.

Arguments:
[SERVER IP:PORT] [# CLIENTS] ([CLIENT IP:PORT]s)
*/

#include "practical.h"

// POSIX Semaphores 
//#include <sys/sem.h>
// POSIX Shared Memory
//#include <sys/shm.h>

#include <pthread.h>

void RequestNewData(struct State* rcv_state, int seq_num);
void PrintSocketAddress(const struct sockaddr *address, FILE *stream);
void UpdateState(struct State* curr_state, struct State* new_state);
void *clientThread();
void *serverThread();

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
struct State *state_vector = NULL;
struct State *local_state;
int num_clients;
char *server_ip;
char *server_port;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

int main(int argc, char *argv[]){

    /* ------------------ Setup ------------------ */
    const char DELIM = ':';
    num_clients = atoi(argv[2]);

    server_ip = strtok(argv[1], &DELIM);
    server_port = strtok(NULL, "\0");

    printf("Server ip: %s, server port: %s. \n", server_ip, server_port);

    if (argc != 3 + num_clients){
        DieWithUserMessage("Parameter(s)", "Incorrect number of arguments");
    } // Test for correct number of arguments

    if (num_clients < 0){
        DieWithUserMessage("Parameter(s)", "# of CLIENTS must be >= 0.");
    }

    char *ipPorts[num_clients];

    for (int i = 3; i < 3 + num_clients; i++){
        ipPorts[i-3] = argv[i];
        printf("ipPorts[%d]: %s \n", i-3, ipPorts[i-3]);
    }

    char *ips[num_clients];
    char *ports[num_clients];

    // Split up client IP:PORTS.
    for (int i = 0; i < num_clients; i++) {
        printf("ipPorts[%d]: %s \n", i, ipPorts[i]);
        ips[i] = strtok(ipPorts[i], &DELIM);
        ports[i] = strtok(NULL, "\n");
        printf("ips[%d]: %s. ports[%d] %s \n", i, ips[i], i, ports[i]);
    }

    for (int i = 0; i < num_clients; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ips[i], ports[i]);
    }
    
    // Create state vector.
    //struct State *stateVector[num_states];
    state_vector = (struct State*)malloc(sizeof(struct State) * num_clients);
    for (int i = 0; i < num_clients; i++) {
        
        // Allocate a new state.
        struct State state;
        struct GPS *gps = (struct GPS*)malloc(sizeof(struct GPS));
        gps->longitude = 0.0;
        gps->latitude = 0.0;
        gps->altitude = 0.0;
        time_t now = time(NULL);
        
        // Load default state into state vector.
        inet_pton(AF_INET, ips[i], &state.ipv4);
        state.port = atoi(ports[i]);
        state.gpsState = gps;
        state.seqNum = 0;
        state.timestamp = now;//gmtime(now);
        state.classification = NOT_DISASTER;
        state.isValid = true;
        // Set vector.
        state_vector[i] = state;
    }

    // Allocate local state.
    struct State* local = (struct State*)malloc(sizeof(struct State));
    if (local == NULL) {
        DieWithSystemMessage("malloc memory allocation failed.");
    }
    struct GPS *gps = (struct GPS*)malloc(sizeof(struct GPS));
    gps->longitude = 0.0;
    gps->latitude = 0.0;
    gps->altitude = 0.0;
    time_t now = time(NULL);
    
    // Load default state.
    inet_pton(AF_INET, server_ip, &local->ipv4);
    local->port = atoi(server_port);
    local->gpsState = gps;
    local->seqNum = 0;
    local->timestamp = now;//gmtime(now);
    local->classification = NOT_DISASTER;
    local->isValid = true;
    // Set vector.
    local_state = local;

    //state_vector = &stateVector;

    pthread_t server_thread;
    pthread_t client_thread;

    pthread_create(&server_thread, NULL, serverThread, NULL);
    pthread_create(&client_thread, NULL, clientThread, NULL);

    pthread_join(server_thread, NULL);
    pthread_join(client_thread, NULL);

    return 0;
}


void *serverThread() {
    printf("Server thread started.\n");

    // Construct the server address structure
    struct addrinfo addrCriteria; // Criteria for address
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_INET; // Any address family
    addrCriteria.ai_flags = AI_PASSIVE; // Accept on any address/port
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram socket
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP socket

    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(NULL, server_port, &addrCriteria, &servAddr);
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
        struct State rcv_state;
        struct sockaddr_storage clntAddr; // Client address
        // Set Length of client address structure (in-out parameter)
        socklen_t clntAddrLen = sizeof(clntAddr);

        // Block until receive message from a client
        ssize_t numBytesRcvd = recvfrom(sock, &rcv_state, sizeof(struct State), 0,
            (struct sockaddr *) &clntAddr, &clntAddrLen);
        if (numBytesRcvd < 0)
            DieWithSystemMessage("recvfrom() failed");

        fputs("Server: Handling client ", stdout);
        PrintSocketAddress((struct sockaddr *) &clntAddr, stdout);
        fputc('\n', stdout);

        for (int i = 0; i < num_clients; i++) {
            printf("Server: check stateVector %d\n", i);
            pthread_mutex_lock(&mutex);
            struct State curr_state = state_vector[i];
            //curr_state.seqNum++;
            if (curr_state.ipv4.s_addr == rcv_state.ipv4.s_addr && curr_state.seqNum < rcv_state.seqNum) {
                printf("Server: set new data\n");
                //RequestNewData(rcv_state, curr_state.seqNum);
                state_vector[i] = rcv_state;
                pthread_mutex_unlock(&mutex);
                break;
            }
            pthread_mutex_unlock(&mutex);
        }
    }
    // NOT REACHED
}

void *clientThread() {

    // Tell the system what kind(s) of address info we want
    struct addrinfo addrCriteria; // Criteria for address match
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_UNSPEC; // Any address family

    // For the following fields, a zero value means "don't care"
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram sockets
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP protocol

    // Get address(es)
    char str[20];
    sprintf(str, "%d", state_vector[0].port);
    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(server_ip, str, &addrCriteria, &servAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create a datagram/UDP socket
    int sock = socket(servAddr->ai_family, servAddr->ai_socktype,
    servAddr->ai_protocol); // Socket descriptor for client
    if (sock < 0)
        DieWithSystemMessage("socket() failed");

    while(true){
        struct State curr_state;

        // Send to the server
        ssize_t numBytes = sendto(sock, &local_state, sizeof(struct State), 0,
        servAddr->ai_addr, servAddr->ai_addrlen);
        if (numBytes < 0)
            DieWithSystemMessage("sendto() failed");
        else if (numBytes != sizeof(struct State))
            DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
        
        local_state->seqNum++;
        
        for (int i = 0; i < num_clients; i++){
            pthread_mutex_lock(&mutex);
            state_vector[i].seqNum++; // FOR TESTING
            curr_state = state_vector[i];
            if (curr_state.isValid){
                printf("Client: sending state %d -- %s:%d.\n", i, inet_ntoa(state_vector[i].ipv4), state_vector[i].port);
                ssize_t numBytes = sendto(sock, &curr_state, sizeof(struct State), 0, servAddr->ai_addr, servAddr->ai_addrlen);
                if (numBytes < 0)
                    DieWithSystemMessage("sendto() failed");
                else if (numBytes != sizeof(struct State))
                    DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
            }
            pthread_mutex_unlock(&mutex);
        }
        sleep(1);
    }
    freeaddrinfo(servAddr);
}


/*
void *clientThread() {
    printf("Client thread started.\n");
    struct sockaddr_storage destStorage;
    memset(&destStorage, 0, sizeof(destStorage));

    // Get address(es)
    size_t addrSize = 0;
    struct sockaddr_in *destAddr4 = (struct sockaddr_in *) &destStorage;
    destAddr4->sin_family = AF_INET;
    destAddr4->sin_port = (in_port_t) atoi(server_port);
    destAddr4->sin_addr.s_addr = inet_addr("127.0.0.1");
    //destAddr4->sin_addr.s_addr = INADDR_BROADCAST;
    addrSize = sizeof(struct sockaddr_in);

    struct sockaddr *destAddress = (struct sockaddr *) &destStorage;
    // Create a datagram/UDP socket
    int sock = socket(destAddress->sa_family, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0)
        DieWithSystemMessage("socket() failed");

    // Set socket to allow broadcast
    int broadcastPerm = 1;
    if (setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcastPerm, sizeof(broadcastPerm)) < 0)
        DieWithSystemMessage("setsockopt() failed");

    while (true) {
        struct State curr_state;// = (struct State*)malloc(sizeof(struct State));
        //if (curr_state == NULL) {
        //    DieWithSystemMessage("malloc memory allocation failed.");
        //}
        // Broadcast local state
        ssize_t numBytes = sendto(sock, local_state, sizeof(struct State), 0, destAddress, addrSize);
        if (numBytes < 0)
            DieWithSystemMessage("sendto() failed");
        else if (numBytes != sizeof(struct State))
            DieWithUserMessage("sendto() error", "sent unexpected number of bytes");

        for (int i = 0; i < num_clients; i++){
            state_vector[i].seqNum++; // FOR TESTING
            curr_state = state_vector[i];
            if (curr_state.isValid || true){
                printf("Sending state %d -- %s:%d.", i, inet_ntoa(state_vector[i].ipv4), state_vector[i].port);
                ssize_t numBytes = sendto(sock, &curr_state, sizeof(struct State), 0, destAddress, addrSize);
                if (numBytes < 0)
                    DieWithSystemMessage("sendto() failed");
                else if (numBytes != sizeof(struct State))
                    DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
            }
        }
        sleep(1);
    }
    close(sock);
    exit(0);
}
*/


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