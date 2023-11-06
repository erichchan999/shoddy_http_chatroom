'''Client executable. Runs on Python version 3'''

import sys
import os

currentDir = os.path.dirname(os.path.realpath(__file__))
parentDir = os.path.dirname(currentDir)
sys.path.append(parentDir)

import socket
import threading
import queue
import clientSettings
from protocol.protocol import Protocol

'''Initialise client settings from program args'''
def initialiseClientSettings():
    clientSettings.serverName = sys.argv[1]
    clientSettings.serverPort = int(sys.argv[2])
    clientSettings.clientUDPPort = int(sys.argv[3])

'''Send login info to server'''
def login():
    username = input('Username: ')
    password = input('Password: ')

    global clientUsername
    clientUsername = username

    clientConnection.sendMessage(username)
    clientConnection.sendMessage(password)

    loginResult = clientConnection.recvMessage()

    print(loginResult)
    
    if loginResult == 'Welcome to TOOM!':
        return True
    else:
        return False

'''Extract address for username from ATU response from server'''
def getATUAddr(username):
    for line in ATU.splitlines():
        lineSplit = line.split(', ')
        
        lineUsername = lineSplit[0]

        if lineUsername == username:
            lineAddrName = lineSplit[1]
            lineAddrPort = lineSplit[2]
            return lineAddrName, int(lineAddrPort)

'''Upload file to username'''
def upload(addr, username, filename):
    updSocket.sendto(f'{clientUsername}; {filename}'.encode('utf-8'), addr)
    
    with open(f'{filename}', 'rb') as file:
        data = file.read(updPacketSize)
        while data:
            updSocket.sendto(data, addr)
            data = file.read(updPacketSize)

    print(f'\n{filename} has been uploaded.\nEnter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ', end='')

'''Receive UDP packets and demultiplex based on address'''
def fileRecv():
    while True:
        # Try and except block to exit thread when client logs out
        try:
            data, addr = updSocket.recvfrom(updPacketSize)
        except socket.timeout:
            if not loggedIn:
                return
            else:
                continue

        if addr not in recvBufferDict:
            buffer = queue.Queue(0)
            recvBufferDict[addr] = buffer

            decodedDataPacket = data.decode('utf-8')
            
            if decodedDataPacket.isprintable():
                split = decodedDataPacket.split('; ')
                if len(split) == 2:
                    username = split[0]
                    filename = split[1]
            else:
                username = ''
                filename = ''
                recvBufferDict[addr].put(data)
        
            writeDataThread = threading.Thread(target=writeData, name='WriteData', args=(addr, username, filename), daemon=True)
            writeDataThread.start()
        else:
            recvBufferDict[addr].put(data)

'''Read data from buffer and write into file'''
def writeData(addr, username, filename):
    if username == '' or filename == '':
        print('Failed to receive username or filename properly')
        username = 'generic_username'
        filename = 'generic_filename'
    
    fullFilename = username + '_' + filename

    with open(f'{fullFilename}', 'wb') as file:
        while True:
            # Uses a timer to detect end of file, by default recvBufferTimeout = 4
            try:
                data = recvBufferDict[addr].get(block=True, timeout=recvBufferTimeout)
            except queue.Empty:
                recvBufferDict.pop(addr)
                break

            file.write(data)
    
    print(f'\nReceived {filename} from {username}.\nEnter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ', end='')
    

ATU = ''
loggedIn = False
clientUsername = ''
recvBufferLock = threading.Lock()
recvBufferDict = {}
recvBufferTimeout = 4
updPacketSize = 1024

initialiseClientSettings()

# Start server TCP socket
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
clientSocket.connect((clientSettings.serverName, clientSettings.serverPort))

clientConnection = Protocol(clientSocket, clientSettings.serverName, clientSettings.serverPort)

while True:
    if login():
        loggedIn = True
        break

# Start P2P UDP socket
updSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
updSocket.bind(('localhost', clientSettings.clientUDPPort))
updSocket.settimeout(2)

# Start UDP file receiving thread
fileRecvThread = threading.Thread(name='FileRecv', target=fileRecv)
fileRecvThread.loggedIn = True
fileRecvThread.start()

# Send listening UDP Port to server
clientConnection.sendMessage(str(clientSettings.clientUDPPort))

while True:
    request = input('Enter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ')
    
    # Extract commnand and args from request
    requestPart = request.partition('; ')

    command = requestPart[0]
    args = tuple(requestPart[2].split('; '))

    if command == 'UPD':
        if len(args) != 2:
            print('Error. Invalid command!')
            continue

        username =  args[0]
        filename = args[1]

        addr = getATUAddr(username)

        if not addr:
            print(f'{username} is offline')
            continue

        uploadThread = threading.Thread(target=upload, name='Upload', args=(addr, username, filename), daemon=True)
        uploadThread.start()
    else:
        clientConnection.sendMessage(request)
        
        response = clientConnection.recvMessage()

        if command == 'OUT':
            clientSocket.close()

            loggedIn = False

            fileRecvThread.join()
            updSocket.close()

            print(response)
            break
        elif command == 'ATU':
            ATU = response
            print(response)
        else:
            print(response)