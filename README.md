# p2p-tree

This is a peer-to-peer (P2P) group messaging implementation.
All participants are "nodes" where each node is an instance
of the program (`src/node.py`) and acts as both server and client.
Groups are formed by invitations and each member of a group only maintains
connections with its invited members and the member invited it.
The first member of a group does not have inviters
(with a dummy inviter IP address and port `start:0`).
A group is like a tree and messages are relayed by nodes on the tree.

## Dependency

Python >= 3.9

## Usage

TODO
