from struct import *
import binascii
import socket
import sys
import shlex
import string
import threading
#import md5
import hashlib
#import readline
import os
import threading
import time

class RCon(object):
    YELL = 0
    PINFO = 1
    SINFO = 2
    SAY = 3
    KICK = 4
    PUNISH = 5
    BAN = 6
    FF = 7
    RESTART = 8
    GAMETYPE = 9
    MAP = 10
    ROTATE = 11
    MAPLIST = 12
    SETGAMETYPE = 13
    ADDMAP = 14
    AVAILMAPS = 15
    MAPINSERT = 16

    def __init__(self):
        self.serverSocket = None
        
    def connect(self, host, port, pw):

        self.clientSequenceNr = 0
        self.queue = []
        self.receiveBuffer = ''
        
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.serverSocket.connect( ( host, port ) )
        self.serverSocket.setblocking(1)


	# Retrieve this connection's 'salt' (magic value used when encoding password) from server
        getPasswordSaltRequest = self.EncodeClientRequest( [ "login.hashed" ] )
        self.serverSocket.send(getPasswordSaltRequest)

        [getPasswordSaltResponse, self.receiveBuffer] = self.receivePacket(self.serverSocket, self.receiveBuffer)

        [isFromServer, isResponse, sequence, words] = self.DecodePacket(getPasswordSaltResponse)

	# if the server doesn't understand "login.hashed" command, abort
        if words[0] != "OK":
            sys.exit(0);

	# Given the salt and the password, combine them and compute hash value
        salt = words[1].decode("hex")
        passwordHash = self.generatePasswordHash(salt, pw)
        passwordHashHexString = string.upper(passwordHash.encode("hex"))

        # Send password hash to server
        loginRequest = self.EncodeClientRequest( [ "login.hashed", passwordHashHexString ] )
        self.serverSocket.send(loginRequest)

        [loginResponse, self.receiveBuffer] = self.receivePacket(self.serverSocket, self.receiveBuffer)

        [isFromServer, isResponse, sequence, words] = self.DecodePacket(loginResponse)

	# if the server didn't like our password, abort
        if words[0] != "OK":
            sys.exit(0);

        #enableEventsRequest = self.EncodeClientRequest( [ "eventsEnabled", "true" ] )
        #self.serverSocket.send(enableEventsRequest)

        #[enableEventsResponse, self.receiveBuffer] = self.receivePacket(self.serverSocket, self.receiveBuffer)
        #[isFromServer, isResponse, sequence, words] = self.DecodePacket(enableEventsResponse)

        # if the server didn't know about the command, abort
        #if words[0] != "OK":
        #    sys.exit(0);

    def run(self):
        while 1:
            if len(self.queue) > 0:
                currentCommand = self.queue.pop(0)
                self.sndcmd(currentCommand[0], currentCommand[1])
            #time.sleep(.6)

    def addcommand(self, command, target=''):
        self.queue.append([command, target])

    def sndcmd(self, command, target=''):
        #receiveBuffer = ''
        command = self.getCommand(command)
        words = shlex.split(command + ' ' + target)
        request = self.EncodeClientRequest(words)
        try:
            self.serverSocket.send(request)
            #packet = self.serverSocket.recv(4096)
            [packet, self.receiveBuffer] = self.receivePacket(self.serverSocket, self.receiveBuffer)
        except Exception, error:
            print 'error sending command'
            print request
            print error
            self.close()
            return
        [isFromServer, isResponse, sequence, words] = self.DecodePacket(packet)

        return words, isResponse
        #self.printPacket(self.DecodePacket(packet))

    def getCommand(self, command):
        if command == self.YELL:  return 'admin.yell'
        elif command == self.PINFO:  return 'admin.listPlayers'
        elif command == self.SINFO:  return 'serverInfo'
        elif command == self.SAY:   return 'admin.say'
        elif command == self.KICK:  return 'punkBuster.pb_sv_command \'pb_sv_Kick'
        elif command == self.PUNISH:    return 'admin.killPlayer'
        elif command == self.BAN:   return 'punkBuster.pb_sv_command \'pb_sv_banGUID'
        elif command == self.FF:    return 'vars.friendlyFire'
        elif command == self.RESTART:   return 'admin.restartMap'
        elif command == self.GAMETYPE:  return 'admin.getPlaylist'
        elif command == self.SETGAMETYPE:   return 'admin.setPlaylist'
        elif command == self.MAP:   return 'mapList.nextLevelIndex'
        elif command == self.ROTATE:    return 'admin.runNextLevel'
        elif command == self.MAPLIST:   return 'mapList.list'
        elif command == self.ADDMAP:    return 'mapList.append'
        elif command == self.AVAILMAPS: return 'admin.supportedMaps'
        elif command == self.MAPINSERT: return 'mapList.insert'

    def EncodeHeader(self, isFromServer, isResponse, sequence):
        header = sequence & 0x3fffffff
        if isFromServer:
            header += 0x80000000
        if isResponse:
            header += 0x40000000
        return pack('<I', header)

    def DecodeHeader(self, data):
        [header] = unpack('<I', data[0 : 4])
        return [header & 0x80000000, header & 0x40000000, header & 0x3fffffff]

    def EncodeInt32(self, size):
        return pack('<I', size)

    def DecodeInt32(self, data):
        return unpack('<I', data[0 : 4])[0]


    def EncodeWords(self, words):
        size = 0
        encodedWords = ''
        for word in words:
            strWord = str(word)
            encodedWords += self.EncodeInt32(len(strWord))
            encodedWords += strWord
            encodedWords += '\x00'
            size += len(strWord) + 5

        return size, encodedWords

    def DecodeWords(self, size, data):
        numWords = self.DecodeInt32(data[0:])
        words = []
        offset = 0
        while offset < size:
            wordLen = self.DecodeInt32(data[offset : offset + 4])
            word = data[offset + 4 : offset + 4 + wordLen]
            words.append(word)
            offset += wordLen + 5

        return words

    def EncodePacket(self, isFromServer, isResponse, sequence, words):
        encodedHeader = self.EncodeHeader(isFromServer, isResponse, sequence)
        encodedNumWords = self.EncodeInt32(len(words))
        [wordsSize, encodedWords] = self.EncodeWords(words)
        encodedSize = self.EncodeInt32(wordsSize + 12)
        return encodedHeader + encodedSize + encodedNumWords + encodedWords

    # Decode a request or response packet
    # Return format is:
    # [isFromServer, isResponse, sequence, words]
    # where
    #	isFromServer = the command in this command/response packet pair originated on the server
    #   isResponse = True if this is a response, False otherwise
    #   sequence = sequence number
    #   words = list of words

    def DecodePacket(self, data):
        [isFromServer, isResponse, sequence] = self.DecodeHeader(data)
        wordsSize = self.DecodeInt32(data[4:8]) - 12
        words = self.DecodeWords(wordsSize, data[12:])
        return [isFromServer, isResponse, sequence, words]

    ###############################################################################



    # Encode a request packet

    def EncodeClientRequest(self, words):
        #global clientSequenceNr
        packet = self.EncodePacket(False, False, self.clientSequenceNr, words)
        self.clientSequenceNr = (self.clientSequenceNr + 1) & 0x3fffffff
        return packet

    # Encode a response packet

    def EncodeClientResponse(self, sequence, words):
        return self.EncodePacket(False, True, sequence, words)

    ###################################################################################

    # Display contents of packet in user-friendly format, useful for debugging purposes

    def printPacket(self, packet):
        line = ''
        #if (packet[0]):
        #    line += "IsFromServer, "
        #else:
        #    line += "IsFromClient, "
        #
        #if (packet[1]):
        #    line += "Response, "
        #else:
        #    line += "Request, "
        #
        #line += "Sequence: " + str(packet[2])

        if packet[3]:
            line += " Event:"
            for word in packet[3]:
                line += "\"" + word + "\""

        line +='\n'
        print line

    def containsCompletePacket(self, data):
        if len(data) < 8:
            return False
        if len(data) < self.DecodeInt32(data[4:8]):
            return False
        return True

    # Wait until the local receive buffer contains a full packet (appending data from the network socket),
    # then split receive buffer into first packet and remaining buffer data

    def receivePacket(self, socket, receiveBuffer):

        while not self.containsCompletePacket(receiveBuffer):
            receiveBuffer += socket.recv(4096)

        packetSize = self.DecodeInt32(receiveBuffer[4:8])
    
        packet = receiveBuffer[0:packetSize]
        receiveBuffer = receiveBuffer[packetSize:len(receiveBuffer)]

        return [packet, receiveBuffer]


    ###################################################################################

    def generatePasswordHash(self, salt, password):
        #m = md5.new()
        m = hashlib.md5()
        m.update(salt)
        m.update(password)
        return m.digest()

    def containsCompletePacket(self, data):
        if len(data) < 8:
            return False
        if len(data) < self.DecodeInt32(data[4:8]):
            return False
        return True

    # Wait until the local receive buffer contains a full packet (appending data from the network socket),
    # then split receive buffer into first packet and remaining buffer data

    def receivePacket(self, socket, receiveBuffer):

        while not self.containsCompletePacket(receiveBuffer):
            receiveBuffer += socket.recv(4096)

        packetSize = self.DecodeInt32(receiveBuffer[4:8])

        packet = receiveBuffer[0:packetSize]
        receiveBuffer = receiveBuffer[packetSize:len(receiveBuffer)]

        return [packet, receiveBuffer]

    def close(self):
        if self.serverSocket is not None:
            try:
                self.serverSocket.send(self.EncodeClientRequest('quit'))
            except:
                pass
            finally:
                self.serverSocket.close()
                self.serverSocket = None




