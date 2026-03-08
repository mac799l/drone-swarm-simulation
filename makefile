# Makefile for UDP Client-Server project

# Compiler and flags
CC      = gcc
CFLAGS  = -Wall -Wextra -g          # warnings + debug info
LDFLAGS =                         # add libraries here if needed (e.g. -lpthread)

# Source files
CLIENT_SRC  = udp_client.c
SERVER_SRC  = udp_server.c
PRACTICAL_SRC  = practical.c
AES_SRC = aes.c
CJSON_SRC = cJSON.c

# Object files
CLIENT_OBJ  = $(CLIENT_SRC:.c=.o)
SERVER_OBJ  = $(SERVER_SRC:.c=.o)
SHARED_OBJ  = $(PRACTICAL_SRC:.c=.o)
AES_SRC_OBJ = $(AES_SRC:.c=.o)
CJSON_SRC_OBJ = $(CJSON_SRC:.c=.o)

# Executables
CLIENT_EXE  = udp_client
SERVER_EXE  = udp_server

# All targets
all: $(CLIENT_EXE) $(SERVER_EXE)

# Link client executable
$(CLIENT_EXE): $(CLIENT_OBJ) $(SHARED_OBJ)
	$(CC) $^ -o $@ $(LDFLAGS)

# Link server executable
$(SERVER_EXE): $(SERVER_OBJ) $(SHARED_OBJ) $(AES_SRC_OBJ) $(CJSON_SRC_OBJ)
	$(CC) $^ -o $@ $(LDFLAGS)

# Pattern rule: compile any .c to .o
%.o: %.c practical.h
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up
.PHONY: clean
clean:
	rm -f $(CLIENT_EXE) $(SERVER_EXE) *.o

# Optional: run targets (useful for testing)
.PHONY: run-client run-server
run-client: $(CLIENT_EXE)
	./$(CLIENT_EXE)

run-server: $(SERVER_EXE)
	./$(SERVER_EXE)