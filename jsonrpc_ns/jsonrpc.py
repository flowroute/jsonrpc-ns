import socket
import json
import traceback
import logging


class JSONRPCError(Exception):
    pass


class JSONRPCProxy:

    def __init__(self, host, port, version="2.0", connect_timeout=60):
        self.host = host
        self.port = port
        self.version = version
        self._id = 1
        self.timeout = connect_timeout
        self.connect()

    @property
    def _rpcid(self):
        if self._id > 1000000:
            self._id = 0
        self._id += 1
        return self._id

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))

    def close(self):
        self.socket.close()

    def _msg(self, method, params={}, notify=False):
        jsonrpc = {
            "jsonrpc": self.version,
            "method": method,
            "params": params
        }

        if notify is not True:
            rpcid = self._rpcid
            jsonrpc['id'] = rpcid

        string = json.dumps(jsonrpc)
        netstring = str(len(string)) + ":" + string + ","

        if notify:
            return netstring
        else:
            return (rpcid, netstring)

    def request(self, method, params={}, retry=1):

        def do_retry(retry):
            retry -= 1
            if retry < 0:
                raise JSONRPCError("Retries exceeded. Request failed.")

            self.close()
            try:
                self.connect()
            except Exception:
                traceback_string = traceback.format_exc()
                logging.error(traceback_string)
            return self.request(method, params, retry-1)

        try:
            rpcid, netstring = self._msg(method, params)

            self.socket.sendall(netstring)

            byte_length = self.socket.recv(1, socket.MSG_WAITALL)

            if not byte_length:
                return do_retry(retry)

            while byte_length[-1] != ':':
                byte_length += self.socket.recv(1)

            byte_length = int(byte_length[:-1])

            response_string = ''
            response_len = 0
            while response_len < byte_length:
                remainder = byte_length - response_len
                response_string += str(self.socket.recv(remainder))
                response_len = len(response_string)
            response = json.loads(response_string)
        except Exception:
            # Get the traceback
            traceback_string = traceback.format_exc()
            logging.error(traceback_string)
            return do_retry(retry)

        if not 'jsonrpc' in response:
            raise JSONRPCError("Missing 'jsonrpc' version")

        if response['jsonrpc'] != self.version:
            raise JSONRPCError(
                "Bad jsonrpc version. Got {}, expects {}".format(
                    response['jsonrpc'], self.version))

        if not 'id' in response:
            raise JSONRPCError("Missing 'id'")

        if response['id'] != rpcid:
            return self.request(method, params, retry-1)

        last_char = self.socket.recv(1)

        if last_char != ',':
            raise JSONRPCError("Bad netstring: missing comma")

        if 'result' in response:
            return response['result']
        elif 'error' in response:
            raise JSONRPCError(response['error'])
        else:
            raise JSONRPCError('Unknown error. Response: {}'.format(response))

    def notify(self, method, params={}):
        netstring = self._msg(method, params, notify=True)
        try:
            self.socket.sendall(netstring)
        except Exception:
            self.close()
            try:
                # Retry once
                self.connect()
                self.socket.sendall(netstring)
            except Exception:
                raise JSONRPCError("Failed to send.")
