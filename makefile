# Makefile for UDP Client-Server project

# Compiler and flags
CC      = gcc
CFLAGS  = -Wall -Wextra -g          # warnings + debug info
LDFLAGS =                         # add libraries here if needed (e.g. -lpthread)

# Source files
SERVER_SRC  = udp_server.c
PRACTICAL_SRC  = practical.c
AES_SRC = aes.c
HMAC_SRC = sha256.c
CJSON_SRC = cJSON.c

# Object files
SERVER_OBJ  = $(SERVER_SRC:.c=.o)
SHARED_OBJ  = $(PRACTICAL_SRC:.c=.o)
AES_SRC_OBJ = $(AES_SRC:.c=.o)
HMAC_SRC_OBJ = $(HMAC_SRC:.c=.o)
CJSON_SRC_OBJ = $(CJSON_SRC:.c=.o)

# Executable
SERVER_EXE  = udp_server

# All targets
all: $(SERVER_EXE)

# Link server executable
$(SERVER_EXE): $(SERVER_OBJ) $(SHARED_OBJ) $(AES_SRC_OBJ) $(HMAC_SRC_OBJ) $(CJSON_SRC_OBJ)
	$(CC) $^ -o $@ $(LDFLAGS)

# Pattern rule: compile any .c to .o
%.o: %.c practical.h
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up
.PHONY: clean
clean:
	rm -f $(SERVER_EXE) *.o