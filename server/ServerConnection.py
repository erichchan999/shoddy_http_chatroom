'''Server side connection class. Each new TCP connection is handled by an instance of this class'''

import datetime
import threading
from inspect import signature
import threadLock
from protocol.protocol import Protocol
import database
import serverSettings


class ServerConnection(Protocol):
    def __init__(self, connectionSocket, clientName, clientPort):
        super().__init__(connectionSocket, clientName, clientPort)
        self.username = ''
        self.clientUDPPort = 0
        self._commands = {
            'MSG': self._msg, 
            'DLT': self._dlt, 
            'EDT': self._edt, 
            'RDM': self._rdm, 
            'ATU': self._atu, 
            'OUT': self._logout,
        }

    def main(self):
        self._loginLoop()
        self._receiveClientUDPPort()
        self._userlogNewLogin()

        while True:
            command, args = self._getRequest()
            self._doCommand(command, args)

            if command == 'OUT':
                return

    def _loginLoop(self):
        while True:
            username = self.recvMessage()
            password = self.recvMessage()

            with threadLock.loginDataLock:
                if not self._validateUsername(username):
                    self.sendMessage('Invalid username! Please try again.')
                elif self._attemptsRemaining(username) <= 0:
                    self.sendMessage('Your account is blocked due to multiple login failures. Please try again later.')
                elif not self._validatePassword(username, password):
                    database.clientsLogin[username]['loginAttempts'] += 1
                    
                    attemptsRemaining = self._attemptsRemaining(username)
                    
                    if attemptsRemaining <= 0:
                        self.sendMessage('Invalid Password! Your account has been timed out. Please try again later.')
                        self._beginEndTimeoutTimer(username)
                    else:
                        self.sendMessage(f'Invalid password! Attempts remaining for this user before timeout: {attemptsRemaining}')
                else:
                    self.username = username
                    
                    self.sendMessage('Welcome to TOOM!')

                    print(f'{username} has logged in.')
                    return

    def _validateUsername(self, username):
        if username in database.clientsLogin:
            return True
        else:
            return False
    
    def _validatePassword(self, username, password):
        if database.clientsLogin[username]['password'] == password:
            return True
        else:
            return False

    '''Login attempts remaining'''
    def _attemptsRemaining(self, username):
        return serverSettings.allowedConsecutiveFailedPasswordAttempts - database.clientsLogin[username]['loginAttempts']

    '''Begin timer to run a function that ends the login timeout'''
    def _beginEndTimeoutTimer(self, username):
        threading.Timer(10.0, self._endTimeout, args=[username]).start()

    '''End login timeout'''
    def _endTimeout(self, username):
        with threadLock.loginDataLock:
            database.clientsLogin[username]['loginAttempts'] = 0

    def _receiveClientUDPPort(self):
        clientUDPPort = int(self.recvMessage())
        self.clientUDPPort = clientUDPPort
    
    '''Update userlog with new login entry'''
    def _userlogNewLogin(self):
        with threadLock.userlogLock:
            with open('userlog.txt', 'a') as userlog:
                userlog.write(f'{database.nextUserlogNumber}; {self._getCurrTimestamp()}; {self.username}; {self.addrName}; {self.clientUDPPort}\n')
            # Update nextUserlogNumber when there is a new login entry
            database.nextUserlogNumber += 1
    
    def _getRequest(self):
        # Each request has format 'COMMAND; arg1; arg2; arg3; ...; arg(n)'
        request = self.recvMessage()

        requestSplit = request.split('; ')
        
        command = requestSplit[0]
        args = tuple(requestSplit[1:])

        return command, args

    def _doCommand(self, command, args):
        if command not in self._commands:
            print(f'{self.username} issued an invalid command.')
            self.sendMessage('Error. Invalid command!')
            return
        
        commandFunc = self._commands[command]
        # Get number of args from the function corresponding to command
        numberOfArgs = len(signature(commandFunc).parameters)

        if len(args) != numberOfArgs:
            print(f'{self.username} issued an invalid command.')
            self.sendMessage('Error. Invalid command!')
            return
        
        if args:
            self._commands[command](*args)
        else:
            self._commands[command]()
        
    def _msg(self, message):
        currTime = self._getCurrTimestamp()

        if message == '':
            self.sendMessage('Invalid message was sent.')
            print(f'{self.username} attempts to send a message, but has provided an invalid message.')
            return
        
        with threadLock.messagelogLock:
            messageNumber = database.nextMessageNumber
            
            with open('messagelog.txt', 'a') as messagelog:
                messagelog.write(f'{messageNumber}; {currTime}; {self.username}; {message}; no\n')

            # Update nextMessageNumber when new message is sent
            database.nextMessageNumber += 1

        self.sendMessage(f'Message #{messageNumber} posted at {currTime}.')

        print(f'{self.username} posted MSG #{messageNumber} "{message}" at {currTime}.')

    def _dlt(self, messageNumber, timestamp):
        currTime = self._getCurrTimestamp()

        try:
            messageNumber = int(messageNumber)
        except:
            self.sendMessage('Invalid message number.')
            print(f'{self.username} attempts to delete MSG #{messageNumber} but has provided an invalid message number.')
            return

        with threadLock.messagelogLock:
            if messageNumber not in range(1, database.nextMessageNumber):
                self.sendMessage('Invalid message number.')
                print(f'{self.username} attempts to delete MSG #{messageNumber} but has provided an invalid message number.')
                return
            
            with open('messagelog.txt', 'r') as messagelog:
                lines = messagelog.readlines()
            
            line = lines[messageNumber - 1]
            lineSplit = line.split('; ')

            lineTimestamp = lineSplit[1]
            lineUsername = lineSplit[2]
            lineMessage = lineSplit[3]
            
            if timestamp != lineTimestamp:
                self.sendMessage(f'Invalid timestamp for message #{messageNumber}.')
                print(f'{self.username} attempts to delete MSG #{messageNumber} at {currTime} but has provided an invalid timestamp.')
                return

            if self.username != lineUsername:
                self.sendMessage(f'Unauthorised to delete message #{messageNumber}.')
                print(f'{self.username} attempts to delete MSG #{messageNumber} at {currTime}. Authorisation fails.')
                return

            del lines[messageNumber - 1]

            newMessageNumber = 1

            
            for index, line in enumerate(lines):
                lineSplit = line.split('; ')

                lineSplit[0] = str(newMessageNumber)

                lines[index] = '; '.join(lineSplit)

                newMessageNumber += 1

            # Rewrite messagelog file with updated changes
            with open('messagelog.txt', 'w') as messagelog:
                messagelog.write(''.join(lines))

            database.nextMessageNumber -= 1

        self.sendMessage(f'Message #{messageNumber} deleted at {currTime}.')

        print(f'{self.username} deleted MSG #{messageNumber} "{lineMessage}" at {currTime}.')

    def _edt(self, messageNumber, timestamp, message):
        currTime = self._getCurrTimestamp()

        try:
            messageNumber = int(messageNumber)
        except:
            self.sendMessage('Invalid message number.')
            print(f'{self.username} attempts to edit MSG #{messageNumber} but has provided an invalid message number.')
            return
        
        with threadLock.messagelogLock:
            if messageNumber not in range(1, database.nextMessageNumber):
                self.sendMessage('Invalid message number.')
                print(f'{self.username} attempts to edit MSG #{messageNumber} but has provided an invalid message number.')
                return
            
            with open('messagelog.txt', 'r') as messagelog:
                lines = messagelog.readlines()
            
            line = lines[messageNumber - 1]
            lineSplit = line.split('; ')

            lineTimestamp = lineSplit[1]
            lineUsername = lineSplit[2]
            lineMessage = lineSplit[3]
            
            if timestamp != lineTimestamp:
                self.sendMessage(f'Invalid timestamp for message #{messageNumber}.')
                print(f'{self.username} attempts to edit MSG #{messageNumber} at {currTime} but has provided an invalid timestamp.')
                return

            if self.username != lineUsername:
                self.sendMessage(f'Unauthorised to edit message #{messageNumber}.')
                print(f'{self.username} attempts to edit MSG #{messageNumber} at {currTime}. Authorisation fails.')
                return

            newline = f'{messageNumber}; {currTime}; {self.username}; {message}; yes\n'

            lines[messageNumber - 1] = newline

            with open('messagelog.txt', 'w') as messagelog:
                messagelog.write(''.join(lines))
                
        self.sendMessage(f'Message #{messageNumber} edited at {currTime}.')

        print(f'{self.username} edited MSG #{messageNumber} "{message}" at {currTime}.')

    def _rdm(self, timestamp):
        try:
            dtTime = self._stripTime(timestamp)
        except ValueError:
            self.sendMessage('Invalid timestamp.')
            print(f'{self.username} issued RDM command but has provided an invalid timestamp.')
            return
        
        messages = []

        with threadLock.messagelogLock:
            with open('messagelog.txt', 'r') as messagelog:
                for line in messagelog:
                    lineSplit = line.split('; ')

                    lineMessageNumber = lineSplit[0]
                    lineTimestamp = lineSplit[1]
                    lineUsername = lineSplit[2]
                    lineMessage = lineSplit[3]
                    lineEdited = lineSplit[4]
                    
                    lineDtTime = self._stripTime(lineTimestamp)

                    if lineDtTime > dtTime:
                        editOrPost = 'edited' if lineEdited == 'yes\n' else 'posted'
                        messages.append(f'#{lineMessageNumber} {lineUsername}: "{lineMessage}", {editOrPost} at {lineTimestamp}\n')

        if messages:
            messagesStr = ''.join(messages)
            self.sendMessage(messagesStr)
        else:
            self.sendMessage('no new message')
        
        print(f'{self.username} issued RDM command\nReturn messages:')
        
        if messages:
            print(messagesStr)
        else:
            print('(no new message)')

    def _atu(self):
        activeUserList = []

        with threadLock.userlogLock:
            with open('userlog.txt', 'r') as userlog:
                for line in userlog:
                    lineSplit = line.split('; ')

                    lineTimestamp = lineSplit[1]
                    lineUsername = lineSplit[2]
                    lineAddrName = lineSplit[3]
                    lineUDPPort = lineSplit[4].rstrip('\n')

                    if lineUsername != self.username:
                        activeUserList.append(f'{lineUsername}, {lineAddrName}, {lineUDPPort}, active since {lineTimestamp}\n')
        
        if activeUserList:
            activeUserStr = ''.join(activeUserList)
            self.sendMessage(activeUserStr)
        else:
            self.sendMessage('no other active user')

        print(f'{self.username} issued ATU command\nReturn active user list:')

        if activeUserList:
            print(activeUserStr)
        else:
            print('(no other active user)')   

    def _logout(self):
        with threadLock.userlogLock:
            with open('userlog.txt', 'r') as userlog:
                lines = userlog.readlines()
                
            for index, line in enumerate(lines):
                lineSplit = line.split('; ')
                
                lineUsername = lineSplit[2]
                
                if lineUsername == self.username:
                    break

            del lines[index]

            newUserlogNumber = 1

            for index, line in enumerate(lines):
                lineSplit = line.split('; ')

                lineSplit[0] = str(newUserlogNumber)

                lines[index] = '; '.join(lineSplit)

                newUserlogNumber += 1

            # Rewrite userlog file with updated changes
            with open('userlog.txt', 'w') as userlog:
                userlog.write(''.join(lines))

            database.nextUserlogNumber -= 1

        self.sendMessage(f'Bye, {self.username}!')

        self.socket.close()

        print(f'{self.username} logout')

    def _getCurrTimestamp(self):
        return datetime.datetime.now().strftime('%d %b %Y %H:%M:%S')

    def _stripTime(self, timeStr):
        return datetime.datetime.strptime(timeStr, '%d %b %Y %H:%M:%S')
    




        