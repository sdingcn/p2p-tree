# p2p-tree

![](https://github.com/sdingcn/p2p-tree/actions/workflows/run_test.yml/badge.svg)

This is a peer-to-peer (P2P) group message application based on TCP.
Group members are "nodes" where every node is an instance
of the program (`node.py`) and acts as both server and client.
Groups are formed by invitations and each member only maintains
connections with its invited members and the member that invited it.
The first member of a group has no inviter.
A group's topology is a tree and messages are relayed by nodes on the tree.

## usage

There are two modes of usage: GUI and CLI.
GUI supports one-line messages (including empty lines)
while CLI only supports non-empty one-line messages
because empty lines are used to signal termination.
Run `python3 node.py` to see the detailed arguments to launch a node.

## tests

`python3 test.py`

## dependency

+ Python >= 3.10
+ IPv4

## packets

Packets (over TCP) are of fixed-length (128 bytes).

## stability

The disconnection of one node may split the group (tree)
into multiple smaller groups.

## NAT

NAT hole punching is not supported.
