# -*- coding: utf-8 -*-
import socket
mac = "44:27:45:d7:23:a6"
mac_bytes = bytes.fromhex(mac.replace(":", ""))
magic = bytes([255]) * 6 + mac_bytes * 16
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(magic, ("255.255.255.255", 9))
sock.close()
print("WoL sent to", mac)
