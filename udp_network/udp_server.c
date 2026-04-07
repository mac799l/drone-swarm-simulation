/*

File: udp_server.c
Project: UDP Network Backend
Description:
    Creates a UDP server/client backend for the Airsim drone simulation. Uses
    AES-128 (tiny-aes-c by kokke) and a SHA256 HMAC (hmac_sha256 by h5p9sl)
    to secure communications.
    Intended to be called by udp_airsim_single_cls.py.

Arguments:
[SERVER IP:PORT] [read pipe fd] [write pipe fd] [# NODES] ([NODE IP:PORT]s)

NOTE: The NODES are for each node in the network, not just the clients.
Node IP:PORTS should be provided in order.
*/

#define CTR 1
#define CBC 0
#define ECB 0
#define AES128 1

#define MAX_NODES 4
#define HMAC_KEY_SIZE 16

#include "practical.h"
#include "aes.h"
#include "cJSON.h"
#include <pthread.h>
#include <time.h>
#include <sys/random.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <netdb.h>


void *serverThread();
void *clientThread();
void *localPipeThread(void *arg);
void *vectorPipeThread(void *arg);
cJSON *stateToJson(int id, struct State *s);
int jsonToState(char *json, struct State *s);
void printStructBytes(void *ptr, size_t size);
void initializeKeys();
void generateRandomIV(u_int8_t *iv);

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

enum messageType {
    UPDATE = 0,
    REQUEST = 1
};

struct node *state_vector;
//struct State *local_state;
int num_clients;
char *server_ip;
char *server_port;


u_int8_t my_node_id = 0;

// Define matrices for directional encryption and HMAC keys.
uint8_t enc_keys[MAX_NODES][MAX_NODES][16];
uint8_t hmac_keys[MAX_NODES][MAX_NODES][16];

int main(int argc, char *argv[]){

    // For debugging.
    printf("Num args: %d\n", argc);
    for (int i = 0; i < argc; i++) {
        printf("argv[%d]: %s\n", i, argv[i]);
    }

    /* ------------------ Setup ------------------ */
    num_clients = atoi(argv[4]);
    server_ip = strtok(argv[1], ":");
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

    // Generate key matrices.
    initializeKeys(); // TESTING ONLY.

    char *ipPorts[num_clients];

    for (int i = 5; i < 5 + num_clients; i++){
        ipPorts[i-5] = argv[i];
        printf("ipPorts[%d]: %s \n", i-5, ipPorts[i-5]);
    }

    char *ips[num_clients];
    char *ports[num_clients];

    // Split up client IP:PORTS.
    for (int i = 0; i < num_clients; i++) {
        ips[i] = strtok(ipPorts[i], ":");
        ports[i] = strtok(NULL,":");

        if (strcmp(ips[i], server_ip) == 0) {
            printf("Detected match. ip: %s. server_ip: %s\n", ips[i], server_ip);
            my_node_id = i;
        }
        printf("ips[%d]: %s. ports[%d] %s \n", i, ips[i], i, ports[i]);
    }

    for (int i = 0; i < num_clients; i++) {
        printf("Client #%d, IP: %s, Port: %s\n", i, ips[i], ports[i]);
    }
    
    // Create state vector.
    state_vector = (struct node*)malloc(sizeof(struct node) * num_clients);
    for (int i = 0; i < num_clients; i++) {
        
        // Allocate a new state.
        struct node node;
        
        // Load default state into state vector.
        inet_pton(AF_INET, ips[i], &node.state.ipv4);
        node.state.port = atoi(ports[i]);
        node.state.gpsState.altitude = 0.0;
        node.state.gpsState.latitude = 0.0;
        node.state.gpsState.longitude = 0.0;
        node.state.seqNum = 0;
        node.state.classification = NOT_DISASTER;
        node.state.isValid = true;

        time_t now = time(NULL);
        node.state.timestamp = now;//gmtime(now);

        if (pthread_mutex_init(&node.mutex, NULL) != 0) {
            DieWithSystemMessage("pthread_mutex_init() failed");
        }
        
        // Set vector.
        state_vector[i] = node;
    }

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
    setvbuf(fp, NULL, _IOLBF, 0);
    struct State *s = (struct State *) malloc(sizeof(struct State));

    while(true){
        char buf[512];
        if (fgets(buf, sizeof(buf), fp) == NULL){
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
        pthread_mutex_lock(&state_vector[my_node_id].mutex);
        state_vector[my_node_id].state.gpsState.altitude = s->gpsState.altitude;
        state_vector[my_node_id].state.gpsState.latitude = s->gpsState.latitude;
        state_vector[my_node_id].state.gpsState.longitude = s->gpsState.longitude;
        state_vector[my_node_id].state.classification = s->classification;
        state_vector[my_node_id].state.timestamp = time(NULL); // Refresh timestamp.
        state_vector[my_node_id].state.seqNum += 1; // Increment sequence.
        pthread_mutex_unlock(&state_vector[my_node_id].mutex);
    }
}

// Send new state vector data to Python program each second.
// TODO: activate on signalling.
void *vectorPipeThread(void *arg){
    FILE *fp = fdopen(*(int *)arg, "w");
    setvbuf(fp, NULL, _IOLBF, 0);
    while(true){

        // Send each state through pipe as a JSON object.
        for(int i = 0; i < num_clients; i++){
            // Don't send local state.
            if (i == my_node_id){
                continue;
            }
            pthread_mutex_lock(&state_vector[i].mutex);
            cJSON *object = stateToJson(i, &state_vector[i].state);
            char *json_str = cJSON_PrintUnformatted(object);
            fprintf(fp, "%s\n", json_str);
            fflush(fp);
            cJSON_Delete(object);
            free(json_str);
            pthread_mutex_unlock(&state_vector[i].mutex);
        }
        // TODO: convert to signaling rather than timers.
        sleep(1); 
    }
}

// Convert state struct to a JSON object.
// For sending data to the Python script.
cJSON *stateToJson(int id, struct State *s){
    cJSON *json = cJSON_CreateObject();
    
    cJSON_AddNumberToObject(json, "id", id);
    cJSON_AddBoolToObject(json, "is_valid", s->isValid);
    cJSON_AddNumberToObject(json, "seq_num", s->seqNum);
    cJSON_AddNumberToObject(json, "classification", s->classification);
    cJSON *gps = cJSON_AddArrayToObject(json, "gps");
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState.latitude));
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState.longitude));
    cJSON_AddItemToArray(gps, cJSON_CreateNumber(s->gpsState.altitude));
    
    return json;
}

// Convert classification and GPS of a JSON message to a state struct.
// For receiving data from the Python script.
int jsonToState(char *json, struct State *s){
    cJSON *parse = cJSON_Parse(json);
    if (!parse){
        return 1;
    }

    cJSON *classification = cJSON_GetObjectItem(parse, "classification");
    cJSON *gps = cJSON_GetObjectItem(parse, "gps");

    s->gpsState.latitude = cJSON_GetArrayItem(gps, 0)->valuedouble;
    s->gpsState.longitude = cJSON_GetArrayItem(gps, 1)->valuedouble;
    s->gpsState.altitude = cJSON_GetArrayItem(gps, 2)->valuedouble;

    s->classification = classification->valueint;

    cJSON_Delete(parse);
    return 0;
}

// Defines the server thread.
void *serverThread() {
    printf("Server thread started.\n");

    // Construct the server address structure
    struct addrinfo addrCriteria; // Criteria for address
    memset(&addrCriteria, 0, sizeof(addrCriteria)); // Zero out structure
    addrCriteria.ai_family = AF_INET; // IPV4 address family
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

    // Allocate a message.
    struct packet *message = (struct packet *) malloc(sizeof(struct packet));
    if (message == NULL){
        DieWithSystemMessage("malloc() failed");
    }

    // For selecting the correct keys.
    uint8_t *dec_key = NULL;
    uint8_t *mac_key = NULL;

    while (true) { // Run forever
        struct sockaddr_storage clntAddr; // Client address
        // Set Length of client address structure (in-out parameter)
        socklen_t clntAddrLen = sizeof(clntAddr);

        // Block until receive message from a client
        ssize_t numBytesRcvd = recvfrom(sock, message, sizeof(struct packet), 0,
            (struct sockaddr *) &clntAddr, &clntAddrLen);
        if (numBytesRcvd < 0)
            DieWithSystemMessage("recvfrom() failed");

        // Verify that the message was sent to the correct node.
        if (message->receiver_id != my_node_id){
            printf("Node ID's don't match.\n");
            memset(message, 0, sizeof(struct packet));
            continue;
        }

        // Get the decryption and HMAC keys for this message.
        dec_key = enc_keys[message->sender_id][my_node_id];
        mac_key = hmac_keys[message->sender_id][my_node_id];

        u_int8_t computedHMAC[SHA256_HASH_SIZE];
        hmac_sha256(mac_key, HMAC_KEY_SIZE, (u_int8_t *)message + SHA256_HASH_SIZE, sizeof(struct packet) - SHA256_HASH_SIZE, computedHMAC, SHA256_HASH_SIZE);

        // Verify integrity.
        if (memcmp(message->hmac, computedHMAC, SHA256_HASH_SIZE) != 0){
            printf("HMAC integrity check failed!\n");
            memset(message, 0, sizeof(struct packet));
            continue;
        }

        // Decrypt state in place.
        AES_init_ctx_iv(&ctx, dec_key, message->iv);
        AES_CTR_xcrypt_buffer(&ctx, (uint8_t *)&message->state, sizeof(struct State));

        printf("Server: received classification of %d\n", message->state.classification);

        // Process message and compare
        // received data against state vector.
        if (message->type == REQUEST) {
            // TODO: send local state back.
        }
        else if (message->type == UPDATE) {
            u_int8_t index = message->index;

            // Skip if local state.
            if (index != my_node_id) {

                printf("Server: check stateVector %d\n", index);
                pthread_mutex_lock(&state_vector[index].mutex);
                
                // Check if the received state is newer, otherwise ignore.
                if (state_vector[index].state.seqNum < message->state.seqNum) {
                    
                    // Check if the recieved state is the sender's local state.
                    if (state_vector[index].state.ipv4.s_addr == message->state.ipv4.s_addr) {
                        printf("Server: set new data.\n");
                        state_vector[index].state = message->state;
                    }
                    else { // Sender has newer info from another node.
                        // TODO: request new data from that node.
                    }
                }

                pthread_mutex_unlock(&state_vector[index].mutex);
            }
        }
        // Reset message.
        memset(message, 0, sizeof(struct packet));
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
    addrCriteria.ai_family = AF_INET; // IPV4 address family.

    // For the following fields, a zero value means "don't care"
    addrCriteria.ai_socktype = SOCK_DGRAM; // Only datagram sockets
    addrCriteria.ai_protocol = IPPROTO_UDP; // Only UDP protocol

    // Create a datagram/UDP socket
    int sock = socket(addrCriteria.ai_family, addrCriteria.ai_socktype,
    addrCriteria.ai_protocol); // Socket descriptor for client
    if (sock < 0)
        DieWithSystemMessage("socket() failed");
    
    int current = 0;

    struct AES_ctx ctx;
    struct packet *message = (struct packet *) malloc(sizeof(struct packet));

    uint8_t *enc_key = NULL;
    uint8_t *mac_key = NULL;

    while(true) { // Loop through state vector.

        // Skip if self.
        if (current == my_node_id) {
            current = (current + 1) % num_clients; // Cycle to the next client.
            continue;
        }

        // For the address of the receiver.
        char curr_ip[INET_ADDRSTRLEN];
        char curr_port[20];

        pthread_mutex_lock(&state_vector[current].mutex);
        sprintf(curr_port, "%d", state_vector[current].state.port);
        inet_ntop(AF_INET, &state_vector[current].state.ipv4, curr_ip, sizeof(curr_ip));
        pthread_mutex_unlock(&state_vector[current].mutex);

        struct addrinfo *serverAddr; // List of server addresses
        int rtnVal = getaddrinfo(curr_ip, curr_port, &addrCriteria, &serverAddr);
        if (rtnVal != 0)
            DieWithUserMessage("getaddrinfo() failed", gai_strerror(rtnVal));
        
        // Send all states to node.
        for (u_int8_t i = 0; i < num_clients; i++){
            if (i == current) {
                continue;   // skip sending receiver its own state
            }

            pthread_mutex_lock(&state_vector[i].mutex);

            memcpy(&message->state, &state_vector[i].state, sizeof(struct State));

            pthread_mutex_unlock(&state_vector[i].mutex);

            if (message->state.isValid) { // Skip invalid states.
                // Generate random IV.
                generateRandomIV(message->iv);
                message->type = UPDATE;
                message->receiver_id = current;
                message->sender_id = my_node_id;
                message->index = i; // Index of the state in the vector.
                
                // Select keys.
                enc_key = enc_keys[my_node_id][current];
                mac_key = hmac_keys[my_node_id][current];

                printf("Client: sending classification of %d\n", message->state.classification);
                // Encrypt state and store in packet struct.
                AES_init_ctx_iv(&ctx, enc_key, message->iv);
                AES_CTR_xcrypt_buffer(&ctx, (uint8_t *)&message->state, sizeof(struct State));

                // Create HMAC of the state and update packet struct.
                hmac_sha256(mac_key, HMAC_KEY_SIZE, (u_int8_t *)message + SHA256_HASH_SIZE, sizeof(struct packet) - SHA256_HASH_SIZE, &message->hmac, SHA256_HASH_SIZE);

                // Send message (containing local state).
                ssize_t numBytes = sendto(sock, message, sizeof(struct packet), 0,
                serverAddr->ai_addr, serverAddr->ai_addrlen);
                if (numBytes < 0)
                    DieWithSystemMessage("sendto() failed");
                else if (numBytes != sizeof(struct packet))
                    DieWithUserMessage("sendto() error", "sent unexpected number of bytes");
            }
        }
        current = (current + 1) % num_clients; // Cycle to the next client.
        freeaddrinfo(serverAddr);
        memset(message, 0, sizeof(struct packet));
        sleep(1);
    }
}

// Generate the key matrices (FOR TESTING ONLY)
void initializeKeys(void) {
    for (int src = 0; src < MAX_NODES; src++) {
        for (int dst = 0; dst < MAX_NODES; dst++) {
            if (src == dst) {
                memset(enc_keys[src][dst], 0, 16);
                memset(hmac_keys[src][dst], 0, 16);
                continue;
            }

            for (int k = 0; k < 16; k++) {
                enc_keys[src][dst][k]  = (uint8_t)(src * 31 + dst * 17 + k);
                hmac_keys[src][dst][k] = (uint8_t)(src * 13 + dst * 29 + k);
            }
        }
    }
}

// Generate random IV of AES_BLOCKLEN bytes.
void generateRandomIV(u_int8_t *iv){
    if (RAND_bytes(iv, AES_BLOCKLEN) != 1){
        DieWithSystemMessage("getrandom() failed");
    }
}