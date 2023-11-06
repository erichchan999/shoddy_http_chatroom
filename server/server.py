'''
Server executable. 
Runs in Python version 3. 
Please put messagelog.txt, userlog.txt and credentials.txt
into the server folder before running.
'''

import sys
import os

currentDir = os.path.dirname(os.path.realpath(__file__))
parentDir = os.path.dirname(currentDir)
sys.path.append(parentDir)

from socket import *
import threading
from ServerConnection import ServerConnection
import serverSettings
import database

'''Initialise server settings from program args'''
def initialiseServerSettings():
    serverSettings.serverPort = int(sys.argv[1])

    try:
        allowedConsecutiveFailedPasswordAttempts = int(sys.argv[2])
    except:
        print(f'Invalid number of allowed failed consecutive attempt: {sys.argv[2]}. The valid value of argument number is an integer between 1 and 5')
        sys.exit()

    if allowedConsecutiveFailedPasswordAttempts not in range(1, 6):
        print(f'Invalid number of allowed failed consecutive attempt: {sys.argv[2]}. The valid value of argument number is an integer between 1 and 5')
        sys.exit()
    
    serverSettings.allowedConsecutiveFailedPasswordAttempts = allowedConsecutiveFailedPasswordAttempts

'''Initialise server database'''
def initialiseDatabase():
    # Extract username and password pairs and initialise login attempts to database 
    with open('credentials.txt', 'r') as credentials:
        for line in credentials:
            lineSplit = line.split()
            username = lineSplit[0]
            password = lineSplit[1].rstrip('\n')

            database.clientsLogin[username] = {
                'password': password,
                'loginAttempts': 0,
            }

    # Truncate userlog.txt file
    with open('userlog.txt', 'w') as userlog:
        pass
    
    database.nextUserlogNumber = 1

    # Initialise nextMessageNumber from messagelog.txt   
    with open('messagelog.txt', 'r') as messagelog:
        try:
            lines = messagelog.readlines()
            lastLine = lines[-1]
            lastLineSplit = lastLine.split('; ')
            database.nextMessageNumber = int(lastLineSplit[0]) + 1
        except:
            database.nextMessageNumber = 1


initialiseServerSettings()
initialiseDatabase()

# Open server TCP socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('localhost', serverSettings.serverPort))
serverSocket.listen()

print(f'Server started. Now listening on port {serverSettings.serverPort}...')

while True:
    connectionSocket, clientAddr = serverSocket.accept()

    client = ServerConnection(connectionSocket, clientAddr[0], clientAddr[1])

    # Start server connection thread
    clientThread = threading.Thread(name='ClientThread', target=client.main)
    clientThread.start()


