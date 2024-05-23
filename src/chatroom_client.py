# -*- coding: utf-8 -*-
"""
Created on Mon May 13 2024
Elaborato traccia 1 - Programmazione di reti 
@author: giovanni.tentelli@studio.unibo.it
0000921144 Giovanni Tentelli
"""
import socket
from threading import Thread, Lock, Event
import sys
import time
import atexit

BUFSIZ = 1024
RECONNECT_ATTEMPTS = 5
EXIT = Event()
RESTART_CONNECTION = Event()
QUIT = "!quit"
PING = "&"


def connection_maintainer(client, lock, EXIT, RESTART_CONNECTION):
    while True:
        if EXIT.is_set() or RESTART_CONNECTION.is_set():
            lock.acquire()
            client.close()
            lock.release()
            return None
        time.sleep(5)
        try:
            client.send(bytes(PING, "utf8"))

        except socket.error as e:
            print("connection maintainer error: {}".format(e))
            lock.acquire()
            RESTART_CONNECTION.set()
            client.close()
            lock.release()
            return None


def connect(address):
    attempts = 0
    while attempts < RECONNECT_ATTEMPTS:
        try:
            attempts = attempts + 1
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(address)
            s.settimeout(15)
            return s
        except socket.error as e:
            print("socket error: {}, reconnecting".format(e))
            print("attempt n.", attempts)
            time.sleep(5)
    print("connection attempts failed, shutting down...")
    sys.exit(1)


def receiver(client, lock, EXIT, RESTART_CONNECTION):
    while True:
        if EXIT.is_set() or RESTART_CONNECTION.is_set():
            lock.acquire()
            client.close()
            lock.release()
            return None
        try:
            msg = client.recv(BUFSIZ).decode("utf8")
            if msg == PING:
                pass
            elif len(msg):
                print(msg)
            else:
                raise socket.error
        except socket.error as e:
            print("{}".format(e))
            lock.acquire()
            RESTART_CONNECTION.set()
            client.close()
            lock.release()
            return None
        except Exception as e:
            print("{}".format(e))
            lock.acquire()
            EXIT.set()
            client.close()
            lock.release()
            return None


def sender(client, lock, EXIT, RESTART_CONNECTION):
    while True:
        try:
            if EXIT.is_set() or RESTART_CONNECTION.is_set():
                lock.acquire()
                client.close()
                lock.release()
                return None
            msg = input().strip()
            if len(msg) and msg != PING:
                client.send(bytes(msg, "utf8"))

            if msg == QUIT:
                print("Quitting application!")
                lock.acquire()
                EXIT.set()
                client.close()
                lock.release()
                return None
            msg = ''

        except socket.error as e:
            print("Could not send message! Error {} occurred".format(e))
            lock.acquire()
            RESTART_CONNECTION.set()
            client.close()
            lock.release()
            return None
        except Exception as e:
            print("{}".format(e))
            lock.acquire()
            EXIT.set()
            client.close()
            lock.release()
            return None


def main():
    HOST = input("Insert host server:")

    try:
        socket.inet_aton(HOST)  # check if address is valid
    except socket.error as e:
        print("{}".format(e))
        print("exiting application")
        sys.exit(1)

    PORT = input("Insert host server port:")

    if not PORT:
        PORT = 50000
    else:
        PORT = int(PORT)

    ADDR = (HOST, PORT)

    def close_socket():
        client.close()

    atexit.register(close_socket)

    lock = Lock()

    while True:
        client = connect(ADDR)
        print("Connection successful!\n")
        if client is not None:
            maintainer_thread = Thread(target=connection_maintainer, args=(client, lock, EXIT, RESTART_CONNECTION))
            maintainer_thread.start()
            receiver_thread = Thread(target=receiver, args=(client, lock, EXIT, RESTART_CONNECTION))
            receiver_thread.start()
            sender_thread = Thread(target=sender, args=(client, lock, EXIT, RESTART_CONNECTION))
            sender_thread.daemon = True
            sender_thread.start()

            while True:
                time.sleep(5)
                if EXIT.is_set():
                    close_socket()
                    print("Application closed!")
                    sys.exit(0)
                elif RESTART_CONNECTION.is_set():
                    print("no message, connection has closed!")
                    close_socket()
                    maintainer_thread.join()
                    receiver_thread.join()
                    print("press enter to continue...")
                    sender_thread.join()
                    lock.acquire()
                    RESTART_CONNECTION.clear()
                    lock.release()
                    break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
