/*
Author: Cameron Lira
File: udp_server.c
Project: CS395 UDP Broadcast Project

Description:
    Defines the UDP server.

Arguments:
[SERVER IP:PORT] [# CLIENTS] ([CLIENT IP:PORT]s)
*/

#define CTR 1
#define CBC 0
#define ECB 0
#define AES128 1

#include "practical.h"
#include "aes.h"
// POSIX Semaphores 
//#include <sys/sem.h>
// POSIX Shared Memory
//#include <sys/shm.h>

#include <pthread.h>
#include <time.h>
#include "cJSON.h"
void PrintSocketAddress(const struct sockaddr *address, FILE *stream);
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

const int BUFFER_SIZE = 1024;
cJSON **state_vector_ptr;
cJSON *local_state_ptr;
int num_clients;
char *server_ip;
char *server_port;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

uint8_t iv[16]  = { 0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff };
uint8_t key[16] = { 0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6, 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c };

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

    char *ipPorts[num_clients + 1];

    for (int i = 3; i < 3 + num_clients; i++){
        ipPorts[i-3] = argv[i];
        printf("ipPorts[%d]: %s \n", i-3, ipPorts[i-3]);
    }
    ipPorts[num_clients] = argv[1];

    char *ips[num_clients + 1];
    char *ports[num_clients + 1];

    // Split up client IP:PORTS.
    for (int i = 0; i < num_clients; i++) {
        printf("ipPorts[%d]: %s \n", i, ipPorts[i]);
        ips[i] = strtok(ipPorts[i], &DELIM);
        ports[i] = strtok(NULL, "\0");
        printf("ips[%d]: %s. ports[%d] %s \n", i, ips[i], i, ports[i]);
    }
    ips[num_clients] = server_ip;
    ports[num_clients] = server_port;

    for (int i = 0; i < num_clients; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ips[i], ports[i]);
    }
    
    // Create state vector.
    local_state_ptr = malloc(sizeof(cJSON*));
    state_vector_ptr = malloc(sizeof(cJSON*) * num_clients);
    for (int i = 0; i < num_clients; i++) {
        cJSON *state = cJSON_CreateObject();
        // Set default fields.
        //time_t now = time(NULL);
        cJSON_AddBoolToObject(state, "is_valid", 1);
        cJSON_AddStringToObject(state, "ip", ips[i]);
        cJSON_AddStringToObject(state, "port", ports[i]);
        cJSON_AddNumberToObject(state, "seq_num", 0);
        cJSON_AddStringToObject(state, "timestamp", "now");
        cJSON_AddNumberToObject(state, "cls", NOT_DISASTER);
        cJSON_AddArrayToObject(state, "gps");
        // cJSON_String str = "0.0";
        // cJSON_AddItemToArray(state->gps, str);
        if (i < num_clients) {
            state_vector_ptr[i] = state;
        }
        else{
            local_state_ptr = state;
        }
    }

    //state_vector = &stateVector;
    printf("%ld \n", sizeof(struct State));

    //return 0;
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

    //struct AES_ctx ctx;
    //AES_init_ctx_iv(&ctx, key, iv);
    for (;;) { // Run forever
        char buffer[BUFFER_SIZE + 1];
        struct sockaddr_storage clntAddr; // Client address
        // Set Length of client address structure (in-out parameter)
        socklen_t clntAddrLen = sizeof(clntAddr);

        // Block until receive message from a client
        ssize_t numBytesRcvd = recvfrom(sock, &buffer, BUFFER_SIZE, 0,
            (struct sockaddr *) &clntAddr, &clntAddrLen);
        if (numBytesRcvd < 0)
            DieWithSystemMessage("recvfrom() failed");

        buffer[numBytesRcvd] = '\0';

        fputs("Server: Handling client ", stdout);
        PrintSocketAddress((struct sockaddr *) &clntAddr, stdout);
        fputc('\n', stdout);
        //Decrypt message
        //AES_CTR_xcrypt_buffer(&ctx, in, 64);

        cJSON *rcv_state = cJSON_Parse(buffer);
        if (rcv_state == NULL){
            printf("Failed to parse JSON.");
            continue;
        }

        cJSON *rcv_ip = cJSON_GetObjectItem(rcv_state, "ip");
        cJSON *rcv_seq = cJSON_GetObjectItem(rcv_state, "seq_num");
        // Compare recieved data with state vector.
        for (int i = 0; i < num_clients; i++) {
            printf("Server: check stateVector %d\n", i);
            pthread_mutex_lock(&mutex);
            // Get state.
            cJSON *curr_state = state_vector_ptr[i];
            cJSON *cur_ip = cJSON_GetObjectItem(curr_state, "port");
            cJSON *cur_seq = cJSON_GetObjectItem(curr_state, "seq_num");

            if ((cur_ip->valuestring == rcv_ip->valuestring) 
                && (cur_seq->valueint < rcv_seq->valueint)) {
                
                printf("Server: set/get new data\n");
                if (cur_ip->valuestring == rcv_ip->valuestring){
                    state_vector_ptr[i] = rcv_state;
                    // Set as new state.
                    pthread_mutex_unlock(&mutex);
                    break;
                }
                //RequestNewData(rcv_state, curr_state.seqNum);
                state_vector_ptr[i] = rcv_state;
                pthread_mutex_unlock(&mutex);
                break;
            }
            pthread_mutex_unlock(&mutex);
        }
        //cJSON_Delete(rcv_state);
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
    sprintf(str, "%d", atoi(server_port));
    struct addrinfo *servAddr; // List of server addresses
    int rtnVal = getaddrinfo(server_ip, str, &addrCriteria, &servAddr);
    if (rtnVal != 0)
        DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

    // Create a datagram/UDP socket
    int sock = socket(servAddr->ai_family, servAddr->ai_socktype,
    servAddr->ai_protocol); // Socket descriptor for client
    if (sock < 0)
        DieWithSystemMessage("socket() failed");
    

    //struct AES_ctx ctx;
    //AES_init_ctx_iv(&ctx, key, iv);
    //AES_CTR_xcrypt_buffer(&ctx, in, 64);

    while(true){
        cJSON *curr_state;
        char *json = cJSON_PrintUnformatted(local_state_ptr);

        printf("Json length: %ld", strlen(json));
        // Send local state
        ssize_t numBytes = sendto(sock, json, strlen(json), 0,
        servAddr->ai_addr, servAddr->ai_addrlen);
        if (numBytes < 0)
            DieWithSystemMessage("sendto() failed");
        else if (numBytes != sizeof(struct State))
            DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
        
        //free(json);
        //cJSON *seq_num = cJSON_GetObjectItem(local_state_ptr, "seq_num");
        
        // Send rest of state vector
        for (int i = 0; i < num_clients; i++){
            pthread_mutex_lock(&mutex);
            //state_vector[i].seqNum++; // FOR TESTING
            curr_state = state_vector_ptr[i];
            json = cJSON_PrintUnformatted(curr_state);

            cJSON *isValid = cJSON_GetObjectItem(curr_state, "is_valid");
            cJSON *ip = cJSON_GetObjectItem(curr_state, "ip");
            cJSON *port = cJSON_GetObjectItem(curr_state, "port");

            if (isValid->valueint){
                printf("Client: sending state %d -- %s:%d.\n", i, ip->valuestring, port->valueint);
                
                ssize_t numBytes = sendto(sock, json, strlen(json), 0, servAddr->ai_addr, servAddr->ai_addrlen);
                if (numBytes < 0)
                    DieWithSystemMessage("sendto() failed");
                else if (numBytes != sizeof(struct State))
                    DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
            }
            pthread_mutex_unlock(&mutex);
        }
        cJSON_Delete(curr_state);
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