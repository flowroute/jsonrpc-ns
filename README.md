jsonrpc-ns
========

Description
-----------

jsonrpc-ns is a Lightweight JSON-RPC library for building TCP (Netstring) clients.

Installation
------------

Prerequisites:

 * Python (Tested on 2.7)

Usage
-----

    from jsonprc_ns import JSONRPCProxy
    jsonrpc = JSONRPCProxy('some.jsonrpc.server.internal', 7080)
    jsonrpc.request('request_method', {'some': 'data'})
    jsonrpc.notify('notify_method', {'more': 'data'})


See Also
-----
[txjason](https://github.com/flowroute/txjason) for building high concurrency servers and clients on top of Twisted Python.

