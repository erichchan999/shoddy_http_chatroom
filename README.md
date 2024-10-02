# Chatroom Server Using Simple Reliable UDP
A chatroom messaging client server model that communicates via TCP. It uses its own application layer protocol based off of HTTP, but only supports variable content length scatter-gathering of messages. Client post messages to the server and the server saves it in a .txt file. Each client connection spawns a new thread in the server to handle that connection. Clients can also send files to each other through P2P via UDP.

This project exists mainly as practice/sandboxing for me to write my own application layer protocol.

# Running
Run the system on localhost or via your private network. DO NOT port forward the server (highly not recommended) as no security measures have been considered. This system should run on all python 3 versions.

## Server
`cd server`

`python3 server.py <portNumber> <numberOfAllowedLoginAttempts>`

## Client
`cd client`

`python3 client.py <serverName> <serverPort> <clientUDPPort>`

### Logging in
Clients must login to the server with username and password. The existing accounts are listed in `server/credentials.txt`.
By default there is 
- username: user
- password: pass

and also

- username: user1
- password: pass1

### Client requests
- MSG: post a message to chatroom: `MSG; <message>`
- DLT: delete a message from chatroom: `DLT; <message number>; <timestamp>`
- EDT: edit a message that you wrote in the chatroom: `EDT; <message number>; <timestamp>; <new message>`
- RDM: read chatroom messages since timestamp: `RDM; <timestamp>`
- ATU: list active (logged in) users in chatroom: `ATU`
- UPD: upload file to active user: `UPD; <username>; <filename> `

### Timestamp format
dd mth year hour:minutes:seconds

e.g.: 03 Jan 2024 00:12:54

### Calling UPD
When calling UPD, the file `test.txt` has been provided by default for you to test this command. When the upload completes there should be `<sender_username>_test.txt` file in the directory that you're running the receiving client program.
