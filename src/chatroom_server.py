# -*- coding: utf-8 -*-
"""
Created on Mon May 13 2024
Elaborato traccia 1 - Programmazione di reti 
@author: giovanni.tentelli@studio.unibo.it
0000921144 Giovanni Tentelli
"""
import socket
from threading import Thread, Lock
import sys
import atexit

QUIT = "!quit"
PING = "&"


def add_client(client, cl_address):
    CLIENTS[client] = cl_address


def remove_client(client):
    if client in CLIENTS.keys():
        del CLIENTS[client]
    if client in USERNAMES.keys():
        del USERNAMES[client]


def add_username(client, username):
    USERNAMES[client] = username


def send_all_clients(message, sender_name):
    for client in CLIENTS:
        if USERNAMES.get(client) != sender_name:
            try:
                client.send(bytes(sender_name + ": ", "utf8") + message)
            except socket.error as e:
                print("{}".format(e))


def connection_restarter(server, lock):
    while not EXITING:
        acceptor_thread = Thread(target=connection_acceptor, args=(server, lock))
        acceptor_thread.daemon = True
        acceptor_thread.start()
        acceptor_thread.join()


def connection_acceptor(server, lock):
    print("Waiting for clients...\n")
    client = None
    while not EXITING:
        try:
            client, cl_address = server.accept()
            client.settimeout(30)
            if client is not None:
                print("%s:%s is now connected.\n" % cl_address)
                lock.acquire()
                add_client(client, cl_address)
                lock.release()
                client_thread = Thread(target=client_manager, args=(client, lock))
                client_thread.daemon = True
                client_thread.start()
        except socket.timeout:
            return None
        except socket.error as e:
            print("Accepting socket error:{}".format(e))
            if client is not None:
                lock.acquire()
                remove_client(client)
                lock.release()
            return None


def client_manager(client, lock):
    try:
        username = None
        client.send(
            bytes("[SERVER]: Hi! Digit here your name (must be at least 2 characters long), then press enter!",
                  "utf8"))
        username = client.recv(BUFSIZ).decode("utf8").strip()
        while len(username) < 2 or username in USERNAMES.values() or username == QUIT:
            if not len(username) or username == QUIT:
                raise Exception("Client has closed the connection\n")
            elif username == PING:
                client.send(bytes(PING, "utf8"))
            else:
                client.send(
                    bytes("[SERVER]: Name is already taken or smaller than 2 caracthers, please digit another name.",
                          "utf8"))
            username = client.recv(BUFSIZ).decode("utf8").strip()

        lock.acquire()
        add_username(client, username)
        print("user %s:%s " % CLIENTS.get(client), "has chosen username %s\n" % username)
        lock.release()

        msg = "[SERVER]: Welcome %s! To leave chat write !quit." % username
        client.send(bytes(msg, "utf8"))
        data = "%s joined the chat!" % username

        lock.acquire()
        send_all_clients(bytes(data, "utf8"), "[SERVER]")
        lock.release()

        while True:
            data = client.recv(BUFSIZ).decode("utf8")
            if data == QUIT:
                lock.acquire()
                print("Client %s:%s," % CLIENTS.get(client),
                      "with username %s is being removed from userlist. Reason: Quit\n" % USERNAMES.get(client))
                send_all_clients(bytes("%s has quit." % username, "utf8"), "[SERVER]")
                remove_client(client)
                lock.release()
                client.close()
                return None
            elif data == PING:
                client.send(bytes(PING, "utf8"))
            elif len(data) and data != PING:
                lock.acquire()
                send_all_clients(bytes(data, "utf8"), username)
                lock.release()
            else:
                raise socket.error

    except socket.error as e:
        # if any case of socket error always remove client from userlist and terminate thread
        lock.acquire()
        print("User %s:%s has recurred a error: {}\n".format(e) % CLIENTS.get(client))
        if client in USERNAMES.keys():
            print("Client %s:%s," % CLIENTS.get(client),
                  "with username %s is being removed from user list. Reason: Disconnected\n" % USERNAMES.get(client))
            send_all_clients(bytes("%s has disconnected." % USERNAMES.get(client), "utf8"), "[SERVER]")
        else:
            print("Client %s:%s," % CLIENTS.get(client), "is being removed from user list. Reason: Disconnected\n")
        remove_client(client)
        lock.release()
        client.close()
        return None
    except Exception as e:
        print("A Client error as occurred: {}\n".format(e))
        print("Client %s:%s" % CLIENTS.get(client), "is being removed from user list. Reason: Disconnected\n")
        lock.acquire()
        remove_client(client)
        lock.release()
        client.close()
        return None


def main():
    global CLIENTS
    global USERNAMES
    global BUFSIZ
    global EXITING

    CLIENTS = dict()
    USERNAMES = dict()
    BUFSIZ = 1024
    EXITING = False

    HOST = ''
    PORT = 53000

    def close_socket():
        send_all_clients(bytes("server is shutting down", "utf8"), "[SERVER]")
        server.close()

    atexit.register(close_socket)

    lock = Lock()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(None)
    try:
        server.bind((HOST, PORT))
        server.listen()
    except socket.error as e:
        print("during server initialization a error has occurred : {}\n".format(e))
        server.close()
        sys.exit(1)

    restarter_thread = Thread(target=connection_restarter, args=(server, lock))
    restarter_thread.daemon = True
    restarter_thread.start()

    print("Server started!\n")

    while True:
        print("write 'quit' to prompt server shutdown\n")
        if input().strip() == 'quit':
            if input("Are you sure? y/n: ").strip() == "y":
                EXITING = True
                close_socket()
                print("Server closed!")
                sys.exit(0)


if __name__ == "__main__":
    main()
