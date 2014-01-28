from jsonrpc import *


def request(addr, method, data):
    '''Simple single function interface
    for JSON-RPC request that
    creates and destroys a socket for every request.
    '''
    host, port = addr.split(':')
    jsrpc = JSONRPCProxy(host, port)
    r = jsrpc.request(method, data)
    jsrpc.close()
    return r


def notify(addr, method, data):
    '''Simple single function interface
    for JSON-RPC notify that
    creates and destroys a socket for every request.
    '''
    host, port = addr.split(':')
    jsrpc = JSONRPCProxy(host, port)
    r = jsrpc.notify(method, data)
    jsrpc.close()
    return r
