# p2p-tree

This is a peer-to-peer (P2P) group message application based on TCP.
Participants are "nodes" where each node is an instance
of the program (`src/node.py`) and acts as both server and client.
Groups are formed by invitations and each member of a group only maintains
connections with its invited members and the member that invited it.
The first member of a group does not have inviters.
A group's topology is a tree and messages are relayed by nodes on the tree.

## Dependency

Python >= 3.9

## Usage

Launch a node by

```
python3 src/node.py <name> <my-ip> <my-port> \[inviter-ip\] \[inviter-port\]
```

where the first node's inviter is omitted.
Then you can type a line and press `Enter`
to send the line to all nodes on the tree.
At the same time any message sent by any node on the tree
is displayed on every node's `stdout`.
Certain control information is printed to `stderr`.
An empty line terminates the current node.
Note that the termination of a node may split the group
into multiple smaller groups.

## About NAT

This program does not implement NAT hole punching.
You can of course form a group inside a LAN,
but if you want to form a group over the Internet
then at least one peer should have a public IP address
where other peers can connect to.
