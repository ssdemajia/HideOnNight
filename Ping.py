# coding=utf-8
import time

from EventLoop import Timer
import random
import socket
import struct
import const

ICMP_CODE = socket.getprotobyname('icmp')
ICMP_ECHO_REQUEST = 8


def checksum(source_string):
    # I'm not too confident that this is right but testing seems to
    # suggest that it gives the same answers as in_cksum in ping.c.
    sum = 0
    count_to = (len(source_string) / 2) * 2
    count = 0
    while count < count_to:
        this_val = ord(source_string[count + 1])*256+ord(source_string[count])
        sum = sum + this_val
        sum = sum & 0xffffffff # Necessary?
        count = count + 2
    if count_to < len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff # Necessary?
    sum = (sum >> 16) + (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    # Swap bytes. Bugger me if I know why.
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


class PingServer(object):
    def __init__(self, targetAddress, listenAddr, listenPort):

        self.listenPort = listenPort
        self.listenAddr = listenAddr
        self._socket = None
        self._targetAddr = socket.gethostbyname(targetAddress)
        self._timeSend = 0
        self._canSend = True

    def createPacket(self):
        self.packet_id = int((random.random()) % 65535)
        header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, 0, self.packet_id, 1)
        data = 192 * 'Q'
        my_checksum = checksum(header + data)
        header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0,
                             socket.htons(my_checksum), self.packet_id, 1)
        return header + data

    def addToLoop(self, loop):
        self._loop = loop
        loop.addTimer(Timer(3, self.handleTimer))

    def handleTimer(self):
        print('send to target timer')
        if self._canSend:
            if self._socket:
                self._loop.remove(self._socket)
                self._socket.close()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_CODE)
            self._loop.add(self._socket, const.PollType.POLL_READ, self)
            package = self.createPacket()
            self._socket.sendto(package, (self._targetAddr, 1))
            self._timeSend = time.time()
            self._canSend = False

    def handleEvent(self, socket, fd, event):
        if socket == self._socket:
            if event.pollType & const.PollType.POLL_READ:
                data, addr = self._socket.recvfrom(1024)
                icmp_header = data[20:28]
                type, code, checksum, p_id, sequence = struct.unpack(
                    'bbHHh', icmp_header)
                timeReceived = time.time()
                if p_id == self.packet_id:
                    print(timeReceived - self._timeSend)
                    self._canSend = True
                else:
                    raise Exception('WTF?')