## Mini bitTorrent: Peer-To-Peer Tracker & Client

### Description
A minimal portable python bitTorrent.

### Usage
Unzip and launch one of the three available trackers from your system (mac, windows, linux). Specify a host's **IP address** and **port**. This host is now the tracker.
```
$ ./tracker.exe 127.0.0.1 8080
``` 
Make a directory to synchronize with other peers.
```
$ mkdir place_files_to_synchronize_with_network_here
```
Move the fileSynchronizer.py into this directory
```
$ cp fileSynchronizer.py
```
Run the synchronizer, provide the tracker's **IP address** and **port**.
```
$ python .\filesynchronizer.py 127.0.0.1 8080
``` 
You files are now synchronized with all peers on the network, connected to the tracker.

### Dependencies

Python 3.9.
