#!/usr/bin/python3
#==============================================================================
#description     :This is a skeleton code for programming assignment 
#usage           :python Skeleton.py trackerIP trackerPort
#python_version  :3.5
#Authors         :Yongyong Wei, Rong Zheng
#==============================================================================

import socket, sys, threading, json,time,os,ssl
import os.path
import glob
import json
import optparse
import ast

from contextlib import closing
from os import listdir
from os.path import isfile, join

def validate_ip(s):
    """
    Validate the IP address of the correct format
    Arguments: 
    s -- dot decimal IP address in string
    Returns:
    True if valid; False otherwise
    """
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

def validate_port(x):
    """Validate the port number is in range [0,2^16 -1 ]
    Arguments:
    x -- port number
    Returns:
    True if valid; False, otherwise
    """
    if not x.isdigit():
        return False
    i = int(x)
    if i < 0 or i > 65535:
            return False
    return True

def get_file_info():
    """ Get file info in the local directory (subdirectories are ignored) 
    Return: a JSON array of {'name':file,'mtime':mtime}
    i.e, [{'name':file,'mtime':mtime},{'name':file,'mtime':mtime},...]
    Hint: a. you can ignore subfolders, *.so, *.py, *.dll
          b. use os.path.getmtime to get mtime, and round down to integer
    """
    file_arr = []
    for f in listdir('.'):
        if isfile(join('.',f)):
            if not (f.startswith('.') or f.endswith(('.py','.dll','README.md','LICENCE'))):
                # We truncate with int() instead of rounding because of comment made
                # below, instructing us to "round down to integer".
                file_arr.append({"name":f,"mtime":int(os.path.getmtime(f))})

    return file_arr


def check_port_available(check_port):
    """Check if a port is available
    Arguments:
    check_port -- port number
    Returns:
    True if valid; False otherwise
    """
    if str(check_port) in os.popen("netstat -na").read():
        return False
    return True
	
def get_next_available_port(initial_port):
    """Get the next available port by searching from initial_port to 2^16 - 1
       Hint: You can call the check_port_avaliable() function
             Return the port if found an available port
             Otherwise consider next port number
    Arguments:
    initial_port -- the first port to check

    Return:
    port found to be available; False if no port is available.
    """
    # Note: The function check_port_avaliable() is unavailable in Windows.
    # This a temporary probe to find next available port.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.bind(('', 0))
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return probe.getsockname()[1]
    

class FileSynchronizer(threading.Thread):
    def __init__(self, trackerhost,trackerport,port, host='0.0.0.0'):

        threading.Thread.__init__(self)
        #Port for serving file requests
        self.port = port
        self.host = host

        #Tracker IP/hostname and port
        self.trackerhost = trackerhost
        self.trackerport = trackerport

        self.BUFFER_SIZE = 8192

        #Create a TCP socket to communicate with the tracker
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(180)

        #Store the message to be sent to the tracker. 
        #Initialize to the Init message that contains port number and file info.
        #Refer to Table 1 in Instructions.pdf for the format of the Init message
        #You can use json.dumps to convert a python dictionary to a json string
        directory_search = get_file_info()
        
        #Build a dictionary for optimized O(1) search
        self.files = {}
        for f in directory_search:
            self.files[f['name']]=f['mtime']
        
        self.msg = json.dumps({'port':self.port,'files':directory_search})

        #Create a TCP socket to serve file requests from peers.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server.bind((self.host, self.port))
        except socket.error:
            print(('Bind failed %s' % (socket.error)))
            sys.exit()
        self.server.listen(10)

    # Not currently used. Ensure sockets are closed on disconnect
    def exit(self):
        self.server.close()

    #Handle file request from a peer(i.e., send the file content to peers)
    def process_message(self, conn,addr):
        '''
        Arguments:
        self -- self object
        conn -- socket object for an accepted connection from a peer
        addr -- address bound to the socket of the accepted connection
        '''
        #YOUR CODE
        #Step 1. read the file name contained in the request through conn
        #Step 2. read content of that file(assumming binary file <4MB), you can open with 'rb'
        #Step 3. send the content back to the requester through conn
        #Step 4. close conn when you are done.
        
        filename = repr(conn.recv(1024).decode("utf-8"))
        filename = filename[1:-1] # remove quotes

        with open(filename, "rb") as f:
            bytes_read = f.read(1024)
            while bytes_read:
                conn.send(bytes_read)
                bytes_read = f.read(1024)
        conn.close()


    def run(self):
        # Connect and register a session with the tracker
        self.client.connect((self.trackerhost,self.trackerport))
        t = threading.Timer(2, self.sync)
        t.start()
        # Begin listening to incoming connections from peers
        print(('Waiting for connections on port %s' % (self.port)))
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.process_message, args=(conn,addr)).start()


    def get_from_peer(self,ip,port,file):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip,port))
        
        client.sendall(bytes(file,'utf-8'))

        fw = open(file, 'wb')
        l = client.recv(1024)
        while (l):
            fw.write(l)
            l = client.recv(1024)

        fw.close()
        client.close()


    #Send Init or KeepAlive message to tracker, handle directory response message
    #and  request files from peers
    def sync(self):
        print(('connect to:'+self.trackerhost,self.trackerport))
        #Step 1. Send Init msg to tracker (Note init msg only sent once)
        #Note: self.msg is initialized with the Init message (refer to __init__)
        #      then later self.msg contains the Keep-alive message
        self.client.send(bytes(self.msg,'utf-8'))

        #Step 2. now receive a directory response message from tracker
        directory_response_message = self.client.recvfrom(2048)[0]
        #print('received from tracker:', directory_response_message)

        #Step 3. parse the directory response message. If it contains new or
        #more up-to-date files, request the files from the respective peers.
        #NOTE: compare the modified time of the files in the message and
        #that of local files of the same name.
        #Hint: a. use json.loads to parse the message from the tracker
        #      b. read all local files, use os.path.getmtime to get the mtime 
        #         p
        #      c. for new or more up-to-date file, you need to create a socket, 
        #         connect to the peer that contains that file, send the file name, and 
        #         receive the file content from that peer
        #      d. finally, write the file content to disk with the file name, use os.utime
        #         to set the mtime
        tracker = ast.literal_eval(directory_response_message.decode('utf-8'))
        for f in tracker:
            # If the file does not belong to this peer
            if tracker[f]['ip'] != self.host and tracker[f]['port'] != self.port:
                
                # Retrieve file if a peer has an updated version
                if f in self.files and 'mtime' in tracker[f] and self.files[f] < tracker[f]['mtime']:
                    print('Found file that requires update:',f)
                    self.get_from_peer(tracker[f]['ip'],tracker[f]['port'],str(f))

                    # Update file mtime
                    self.files[f] = tracker[f]['mtime']

                # Otherwise retrieve file
                elif not (f in self.files):
                    print('Found new file:',f)
                    self.get_from_peer(tracker[f]['ip'],tracker[f]['port'],str(f))

                    # Add file to records
                    self.files[f] = tracker[f]['mtime']
            


        #Step 4. construct and send the KeepAlive message
        #Note KeepAlive msg is sent multiple times, the format can be found in Table 1
        #use json.dumps to convert python dict to json string.
        self.msg = json.dumps({'port':self.port})

        #Step 5. start timer
        t = threading.Timer(5, self.sync)
        t.start()

if __name__ == '__main__':
    #parse command line arguments
    parser = optparse.OptionParser(usage="%prog ServerIP ServerPort")
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("No ServerIP and ServerPort")
    elif len(args) < 2:
        parser.error("No  ServerIP or ServerPort")
    else:
        if validate_ip(args[0]) and validate_port(args[1]):
            tracker_ip = args[0]
            tracker_port = int(args[1])

        else:
            parser.error("Invalid ServerIP or ServerPort")
    #get free port
    synchronizer_port = get_next_available_port(8000)
    synchronizer_thread = FileSynchronizer(tracker_ip,tracker_port,synchronizer_port)
    synchronizer_thread.start()
