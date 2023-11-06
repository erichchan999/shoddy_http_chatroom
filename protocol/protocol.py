'''
Application layer protocol for sending and receiving messages. 
Each message has the format 'Content-Length: {size of body in bytes}\r\nPAYLOAD DATA...'.
'''
import socket

class Protocol:
    def __init__(self, socket, addrName, addrPort):
        self.socket = socket
        self.addrName = addrName
        self.addrPort = addrPort
        self._recvCarryOverData = ''
    
    '''Send message via TCP'''
    def sendMessage(self, message):
        messageBytes = message.encode('utf-8')

        contentLength = len(messageBytes)

        header = f'Content-Length: {contentLength}\r\n'

        headerBytes = header.encode('utf-8')

        self.socket.sendall(headerBytes)
        self.socket.sendall(messageBytes)


    '''Receive message via TCP'''
    def recvMessage(self):        
        messageStart = []

        messageStart.append(self._recvCarryOverData)

        while '\r\n' not in ''.join(messageStart):
            payload = self.socket.recv(1024).decode('utf-8')
            messageStart.append(payload)
        
        headerSplit = ''.join(messageStart).partition('\r\n')
        header = headerSplit[0]
        afterHeader = headerSplit[2]

        contentLength = int(header.lstrip('Content-Length: '))
        currentLengthOfContentReceived = len(afterHeader)

        content = []

        # Chop excess afterHeader if it is longer than content length
        if currentLengthOfContentReceived > contentLength:
            carryOverAmount = currentLengthOfContentReceived - contentLength
            
            content.append(afterHeader[:-carryOverAmount])
            self._recvCarryOverData = afterHeader[-carryOverAmount:]
        else:
            content.append(afterHeader)
            self._recvCarryOverData = ''

        while currentLengthOfContentReceived < contentLength:
            payload = self.socket.recv(1024).decode('utf-8')
            currentLengthOfContentReceived += len(payload)

            # Chop excess payload if it is longer than content length
            if currentLengthOfContentReceived > contentLength:
                carryOverAmount = currentLengthOfContentReceived - contentLength
                
                content.append(payload[:-carryOverAmount])
                self._recvCarryOverData = payload[-carryOverAmount:]
            else:
                content.append(payload)
                self._recvCarryOverData = ''

        return ''.join(content)