/*
Author: Cameron Lira
File: udp_server.c
Project: CS395 UDP Broadcast Project

Description:
    Creates the UDP server and client.

Arguments:
[SERVER IP:PORT] [read pipe fd] [write pipe fd] [# CLIENTS] ([CLIENT IP:PORT]s)
*/

#define CTR 1
#define CBC 0
#define ECB 0
#define AES128 1

#include "practical.h"
#include "aes.h"
#include <pthread.h>
#include <time.h>
#include "cJSON.h"

void *serverThread();
void *clientThread();
void *localPipeThread(void *arg);
void *vectorPipeThread(void *arg);
cJSON *stateToJson(int id, struct State *s);
int jsonToState(char *json, struct State *s);
void printStructBytes(void *ptr, size_t size);
void PrintSocketAddress(const struct sockaddr *address, FILE *stream);

// Detected classes for use by a YOLO model trained on the MEDIC disaster dataset.
// Can be updated to match your specific model.
enum disasterCls {
    EARTHQUAKE = 0,
    FIRE = 1,
    FLOOD = 2,
    HURRICANE = 3,
    LANDSLIDE = 4,
    NOT_DISASTER = 5,
    OTHER_DISASTER = 6
};

struct State *state_vector;
struct State *local_state;
int num_clients;
char *server_ip;
char *server_port;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t local_mutex = PTHREAD_MUTEX_INITIALIZER;

uint8_t iv[16]  = { 0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff };
uint8_t key[16] = { 0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6, 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c };

int main(int argc, char *argv[]){

    printf("Num args: %d\n", argc);

    for (int i = 0; i < argc; i++) {
        printf("argv[%d]: %s\n", i, argv[i]);
    }
    /* ------------------ Setup ------------------ */
    const char DELIM = ':';
    num_clients = atoi(argv[4]);

    server_ip = strtok(argv[1], &DELIM);
    server_port = strtok(NULL, "\0");

    int *local_pipe_r = malloc(sizeof(int));
    int *vector_pipe_w = malloc(sizeof(int));
    *local_pipe_r = atoi(argv[2]);
    *vector_pipe_w = atoi(argv[3]);

    printf("Server ip: %s, server port: %s. \n", server_ip, server_port);

    if (argc != 5 + num_clients){
        DieWithUserMessage("Parameter(s)", "Incorrect number of arguments");
    } // Test for correct number of arguments

    if (num_clients <= 0){
        DieWithUserMessage("Parameter(s)", "# of CLIENTS must be > 0.");
    }

    char *ipPorts[num_clients];

    for (int i = 5; i < 5 + num_clients; i++){
        ipPorts[i-5] = argv[i];
        printf("ipPorts[%d]: %s \n", i-3, ipPorts[i-5]);
    }

    char *ips[num_clients];
    char *ports[num_clients];

    // Split up client IP:PORTS.
    for (int i = 0; i < num_clients; i++) {
        ips[i] = strtok(ipPorts[i], &DELIM);
        ports[i] = strtok(NULL, "\n");
        printf("ips[%d]: %s. ports[%d] %s \n", i, ips[i], i, ports[i]);
    }

    for (int i = 0; i < num_clients; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ips[i], ports[i]);
    }
    
    // Create state vector.
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
    printf("Struct size: %ld bytes.\n", sizeof(struct State));

    //return 0;
    pthread_t server_thread;
    pthread_t client_thread;
    pthread_t local_pipe_thread;
    pthread_t vector_pipe_thread;

    pthread_create(&server_thread, NULL, serverThread, NULL);
    pthread_create(&client_thread, NULL, clientThread, NULL);
    pthread_create(&local_pipe_thread, NULL, localPipeThread, local_pipe_r);
    pthread_create(&vector_pipe_thread, NULL, vectorPipeThread, vector_pipe_w);

    pthread_join(server_thread, NULL);
    pthread_join(client_thread, NULL);
    pthread_join(local_pipe_thread, NULL);
    pthread_join(vector_pipe_thread, NULL);
    return 0;
}

// Monitor pipe for data from Python program.
void *localPipeThread(void *arg){
    FILE *fp = fdopen(*(int *)arg, "r");
    struct State *s = (struct State *) malloc(sizeof(struct State));    
    while(true){
        char buf[100];
        if (fgets(buf, sizeof(buf), fp) == NULL){
            fflush(fp);
            continue;
        }

        memset(s, 0, sizeof(struct State));
        // Convert JSON message to state elements (GPS, Classification, etc)
        int i = jsonToState(buf, s);
        if (i == 1){
            printf("Failed to parse JSON.\n");
            continue;
        }
        // Update local state.
        pthread_mutex_lock(&local_mutex);
        memcpy(local_state->gpsState, s->gpsState, sizeof(struct GPS));
        memcpy(&local_state->classification, &s->classification, sizeof(u_int8_t));
        local_state->timestamp = time(NULL);
        local_state->seqNum += 1;
        pthread_mutex_unlock(&local_mutex);
    }
}

// Send new state vector data to Python program.
void *vectorPipeThread(void *arg){
    FILE *fp = fdopen(*(int *)arg, "w");
    while(true){
        pthread_mutex_lock(&mutex);
        // Send each state through pipe as a JSON object.
        for(int i = 0; i < num_clients; i++){
            cJSON *object = stateToJson(i, &state_vector[i]);
            char *json_str = cJSON_PrintUnformatted(object);
            fprintf(fp, "%s\n", json_str);
            fflush(fp);
        }
        pthread_mutex_unlock(&mutex);
        sleep(1); 
    }
}

cJSON *stateToJson(int id, struct State *s){
    cJSON *json = cJSON_CreateObject();
    
    cJSON_AddNumberToObject(json, "id", id);
    cJSON_AddBoolToObject(json, "is_valid", s->isValid);
    //char ip[20];
    //inet_ntop(AF_INET, &s->ipv4, ip, strlen(ip));
    //cJSON_AddStringToObject(json, "ip", ip);
    //cJSON_AddNumberToObject(json, "port", s->port);
    cJSON_AddNumberToObject(json, "seq_num", s->seqNum);
    //cJSON_AddNumberToObject(json, "timestamp", s->timestamp);
    cJSON_AddNumberToObject(json, "classification", s->classification);
    cJSON *gps = cJSON_AddArrayToObject(json, "gps");
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState->latitude));
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState->longitude));
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState->altitude));
    return json;
}


int jsonToState(char *json, struct State *s){
    cJSON *parse = cJSON_Parse(json);
    if (!parse){
        return 1;
    }

    //cJSON *is_valid = cJSON_GetObjectItem(parse, "is_valid");
    //cJSON *ip = cJSON_GetObjectItem(parse, "ip");
    //cJSON *port = cJSON_GetObjectItem(parse, "port");
    //cJSON *seq_num = cJSON_GetObjectItem(parse, "seq_num");
    //cJSON *timestamp = cJSON_GetObjectItem(parse, "timestamp");
    cJSON *classification = cJSON_GetObjectItem(parse, "classification");
    cJSON *gps = cJSON_GetObjectItem(parse, "gps");

    s->gpsState->latitude = cJSON_GetArrayItem(gps, 0)->valuedouble;
    s->gpsState->longitude = cJSON_GetArrayItem(gps, 1)->valuedouble;
    s->gpsState->altitude = cJSON_GetArrayItem(gps, 2)->valuedouble;

    //s->isValid = is_valid->valueint;
    //inet_pton(AF_INET, ip->valuestring, &s->ipv4);
    //s->port = port->valueint;
    //s->seqNum = seq_num->valueint;
    //s->timestamp = timestamp->valueint;
    s->classification = classification->valueint;

    cJSON_Delete(parse);
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

    // Prepare for encryption/decryption.
    struct AES_ctx ctx;
    AES_init_ctx_iv(&ctx, key, iv);

    //int current = 0;
    for (;;) { // Run forever
        struct State *rcv_state = (struct State *)malloc(sizeof(struct State));
        struct sockaddr_storage clntAddr; // Client address
        // Set Length of client address structure (in-out parameter)
        socklen_t clntAddrLen = sizeof(clntAddr);

        //char rcv_buf[sizeof(struct State)];
        // Block until receive message from a client
        ssize_t numBytesRcvd = recvfrom(sock, rcv_state, sizeof(struct State), 0,
            (struct sockaddr *) &clntAddr, &clntAddrLen);
        if (numBytesRcvd < 0)
            DieWithSystemMessage("recvfrom() failed");

        //printf("Server: Handling client: ");
        //PrintSocketAddress((struct sockaddr *) &clntAddr, stdout);
        //printf('\n');

        //Decrypt message
        AES_CTR_xcrypt_buffer(&ctx, (uint8_t *)rcv_state, numBytesRcvd);

        pthread_mutex_lock(&mutex);
        for (int i = 0; i < num_clients; i++) {
            printf("Server: check stateVector %d\n", i);
            struct State curr_state = state_vector[i];

            if (curr_state.ipv4.s_addr == rcv_state->ipv4.s_addr && curr_state.seqNum < rcv_state->seqNum) {
                printf("Server: set new data\n");
                state_vector[i] = *rcv_state;
                break;
            }
            else if(curr_state.seqNum < rcv_state->seqNum){
                printf("Request new data.");
                //RequestNewData(rcv_state, curr_state.seqNum);
            }
        }
        pthread_mutex_unlock(&mutex);
    }
    // NOT REACHED
}

// Used for debugging purposes.
void printStructBytes(void *ptr, size_t size) {
    uint8_t *bytes = (uint8_t *)ptr;

    for (size_t i = 0; i < size; i++) {
        printf("%02X ", bytes[i]);
    }
    printf("\n");
}

void *clientThread() {
    printf("Client thread started.\n");
    // Tell the system what kind(s) of address info we want
    struct addrinfo addrCriteria; // Criteria for address match
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_UNSPEC; // Any address family

    // For the following fields, a zero value means "don't care"
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram sockets
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP protocol

    // Create a datagram/UDP socket
    int sock = socket(addrCriteria.ai_family, addrCriteria.ai_socktype,
    addrCriteria.ai_protocol); // Socket descriptor for client
    if (sock < 0)
        DieWithSystemMessage("socket() failed");
    
    // Prepare for encryption.
    struct AES_ctx ctx;
    AES_init_ctx_iv(&ctx, key, iv);

    int current = 0;
    while(true){ // Loop through clients.

        // Get address(es)
        char curr_ip[20];
        char curr_port[20];
        sprintf(curr_port, "%d", state_vector[current].port);
        //sprintf(curr_ip, "%d", state_vector[current].ipv4.s_addr);
        inet_ntop(AF_INET, &state_vector[current].ipv4, curr_ip, 20);
        struct addrinfo *serverAddr; // List of server addresses
        int rtnVal = getaddrinfo(curr_ip, curr_port, &addrCriteria, &serverAddr);
        if (rtnVal != 0)
            DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));

        // Copy local state.
        struct State *state_buf = (struct State *) malloc(sizeof(struct State));
        if (state_buf == NULL){
            DieWithSystemMessage("malloc() failed");
        }
        pthread_mutex_lock(&local_mutex);
        memcpy(state_buf, local_state, sizeof(struct State));
        pthread_mutex_unlock(&local_mutex);

        // Encrypt
        AES_CTR_xcrypt_buffer(&ctx, (uint8_t *)state_buf, sizeof(struct State));

        // Send local state.
        ssize_t numBytes = sendto(sock, &state_buf, sizeof(struct State), 0,
        serverAddr->ai_addr, serverAddr->ai_addrlen);
        if (numBytes < 0)
            DieWithSystemMessage("sendto() failed");
        else if (numBytes != sizeof(struct State))
            DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
        
        //local_state->seqNum++;
        
        // Send state vector states.
        struct State curr_state;
        memset(state_buf, 0, sizeof(struct State)); // Reset memory.
        pthread_mutex_lock(&mutex);
        for (int i = 0; i < num_clients; i++){
            state_vector[i].seqNum++; // FOR TESTING
            curr_state = state_vector[i];
            if (curr_state.isValid){
                state_buf = &curr_state;
                // Encrypt
                AES_CTR_xcrypt_buffer(&ctx, (uint8_t *)state_buf, sizeof(struct State));
                printf("Client: sending state %d -- %s:%d.\n", i, inet_ntoa(state_vector[i].ipv4), state_vector[i].port);
                ssize_t numBytes = sendto(sock, state_buf, sizeof(struct State), 0, serverAddr->ai_addr, serverAddr->ai_addrlen);
                
                if (numBytes < 0)
                    DieWithSystemMessage("sendto() failed");
                else if (numBytes != sizeof(struct State))
                    DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
            }
        }
        pthread_mutex_unlock(&mutex);
        current = (current + 1) % num_clients; // Cycle to the next client.
        freeaddrinfo(serverAddr);
        sleep(1);
    }
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