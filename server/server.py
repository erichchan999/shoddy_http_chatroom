'''
Server executable.
'''

import sys
import socket
import threading
from ServerConnection import ServerConnection
import serverSettings
import database

'''
Initialise server settings from program args
'''
def initialiseServerSettings(port, allowedConsecutiveFailedPasswordAttempts):
    serverSettings.serverPort = int(port)

    try:
        allowedConsecutiveFailedPasswordAttempts = int(allowedConsecutiveFailedPasswordAttempts)
    except:
        print(f'Invalid number of allowed failed consecutive attempt, cannot convert to integer')
        sys.exit()

    if allowedConsecutiveFailedPasswordAttempts not in range(1, 6):
        print(f'Invalid number of allowed failed consecutive attempt: {allowedConsecutiveFailedPasswordAttempts}. Valid value is an integer between 1 and 5')
        sys.exit()
    
    serverSettings.allowedConsecutiveFailedPasswordAttempts = allowedConsecutiveFailedPasswordAttempts

'''
Initialise server database
'''
def initialiseDatabase():
    # Extract username and password pairs and initialise login attempts to database 
    try: 
        with open('credentials.txt', 'r') as credentials:
            for line in credentials:
                lineSplit = line.split()
                assert(len(lineSplit) == 2)
                username = lineSplit[0]
                password = lineSplit[1].rstrip('\n')

                database.clientsLogin[username] = {
                    'password': password,
                    'loginAttempts': 0,
                }
    except:
        print('credentials.txt does not exist or is not formatted correctly, no logins will succeed')
        sys.exit()

    # Truncate userlog.txt file
    open('userlog.txt', 'w').close()
    
    database.nextUserlogNumber = 1

    # Initialise nextMessageNumber from messagelog.txt   
    try:
        with open('messagelog.txt', 'r') as messagelog:
            lines = messagelog.readlines()
            lastLine = lines[-1]
            lastLineSplit = lastLine.split('; ')
            database.nextMessageNumber = int(lastLineSplit[0]) + 1
    except:
        database.nextMessageNumber = 1
        open('messagelog.txt', 'w').close()

# List to keep track of client threads for graceful shutdown
clientThreads = []
clientConnectionSockets = []


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python server.py <server_port> <allowed_consecutive_failed_password_attempts>')
        sys.exit()

    initialiseServerSettings(sys.argv[1], sys.argv[2])
    initialiseDatabase()

    # Open server TCP socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        serverSocket.bind(('localhost', serverSettings.serverPort))
    except:
        print(f'Port {serverSettings.serverPort} is already in use')
        sys.exit()

    serverSocket.listen()

    print(f'Server started. Now listening on port {serverSettings.serverPort}...')

    try:
        while True:
            clientConnectionSocket, clientAddr = serverSocket.accept()

            # Start a new thread for each client connection.
            clientConnection = ServerConnection(clientConnectionSocket, clientAddr[0], clientAddr[1])
            clientConnectionSockets.append(clientConnectionSocket)

            clientThread = threading.Thread(
                name='ClientConnectionThread',
                target=clientConnection.main
            )
            clientThreads.append(clientThread)
            clientThread.start()
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C or other termination signals
        print("Server is shutting down gracefully...")
        # Close all client connection sockets
        for clientConnectionSocket in clientConnectionSockets:
            clientConnectionSocket.close()
        serverSocket.close()
        print("Server has shut down.")



