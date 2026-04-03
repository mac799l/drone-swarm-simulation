CC      = gcc
CFLAGS  = -Wall -Wextra -g
LDFLAGS = 

# Sources and objects
SERVER_SRC    = udp_server.c
PRACTICAL_SRC = practical.c
AES_SRC       = aes.c
SHA_SRC       = sha256.c
HMAC_SRC      = hmac_sha256.c
CJSON_SRC     = cJSON.c

OBJS = $(SERVER_SRC:.c=.o) \
       $(PRACTICAL_SRC:.c=.o) \
       $(AES_SRC:.c=.o) \
       $(SHA_SRC:.c=.o) \
       $(HMAC_SRC:.c=.o) \
       $(CJSON_SRC:.c=.o)

SERVER_EXE = udp_server

DEPFLAGS = -MMD -MP
CFLAGS  += $(DEPFLAGS)

all: $(SERVER_EXE)

$(SERVER_EXE): $(OBJS)
	$(CC) $^ -o $@ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

-include $(OBJS:.o=.d)

.PHONY: clean
clean:
	rm -f $(SERVER_EXE) *.o *.d