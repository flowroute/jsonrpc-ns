from jsonrpc_ns import (JSONRPCProxy, JSONRPCError, JSONRPCBadResponse,
                        JSONRPCResponseError, JSONRPCRequestFailure)
import SocketServer as socketserver
import threading
from itertools import dropwhile
import json
import time


class TestServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


HOSTPORT = ('127.0.0.1', 9099)


class BadSocket:
    def __init__(self, socket=None):
        self.socket = socket
        self.tried = 0

    def sendall(self, *args):
        if self.tried > 0 and self.socket is not None:
            self.socket.sendall(*args)
        else:
            self.tried += 1
            raise Exception('Failed to send.')

    def close(self):
        pass


class JSONRPCHandler(socketserver.BaseRequestHandler):
    '''
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    '''

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()

        # process request
        raw = dropwhile((lambda x: x != ':'), str(self.data))
        jsdata = (''.join(raw))[1:-1]

        # these values can be overridden
        is_error = False
        missing_comma = False
        version = '2.0'
        try:
            data = json.loads(jsdata)
        except:
            return
        result = None
        if 'id' in data:
            _id = data['id']
        method = data['method']

        if method == 'test_request':
            result = 'pass'
        elif method == 'test_request_fail':
            return
        elif method == 'test_no_id':
            _id = None
            result = 'fail'
        elif method == 'test_no_version':
            version = None
            result = 'fail'
        elif method == 'test_bad_version':
            version = '9000'
            result = 'fail'
        elif method == 'test_no_version_error':
            version = None
            is_error = True
            code = 200
            message = 'fail'
        elif method == 'test_notify':
            self.server.got_notify = True
            return
        elif method == 'test_wrong_id_retry':
            if _id <= 1:
                _id = 2
            result = 'pass'
        elif method == 'test_wrong_id_fail':
            return
        elif method == 'test_missing_comma':
            missing_comma = True
            result = 'fail'
        elif method == 'test_error_no_code':
            is_error = True
            code = None
            message = 'foobar'
            result = 'fail'
        elif method == 'test_error_no_message':
            is_error = True
            code = 200
            message = None
            result = 'fail'
        elif method == 'test_error':
            is_error = True
            code = 9000
            message = 'Failed'

        # construct response
        if is_error is False:
            respd = {'jsonrpc': version,
                     'id': _id,
                     'result': result}
        else:
            respd = {'jsonrpc': version,
                     'id': _id,
                     'error': {'code': code,
                               'message': message}}

        if _id is None:
            respd.pop('id')
        if version is None:
            respd.pop('jsonrpc')
        if is_error:
            if code is None:
                respd['error'].pop('code')
            if message is None:
                respd['error'].pop('message')

        resps = json.dumps(respd)
        if not missing_comma:
            response = '{}:{},\n'.format(len(resps), resps)
        else:
            response = '{}:{}\n'.format(len(resps), resps)

        self.request.sendall(response)


class TestJSONRPC:

    def setUp(self):
        self.server = TestServer(HOSTPORT, JSONRPCHandler)
        self.server.got_notify = False
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        #self.server_thread.setDaemon(True)
        self.server_thread.start()
        self.proxy = JSONRPCProxy(*HOSTPORT)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    @classmethod
    def setup_class(cls):
        print ('setup_class() before any methods in this class')

    @classmethod
    def teardown_class(cls):
        print ('teardown_class() after any methods in this class')

    def assertException(self, name, _e, _str, notify=False):
        try:
            if not notify:
                self.proxy.request(name, 'foobar')
            else:
                self.proxy.notify(name, 'foobar')
        except _e as e:
            print _str
            print str(e)
            assert (isinstance(e, JSONRPCError))
            assert (_str in e.value)
            assert (_str in str(e))
            return
        assert False

    def test_request(self):
        result = self.proxy.request('test_request', 'foobar')
        assert (result == 'pass')

    def test_request_fail(self):
        self.assertException('test_request_fail', JSONRPCRequestFailure,
                             'Retries exceeded.')

    def test_notify(self):
        result = self.proxy.notify('test_notify', 'foobar')
        assert (result is None)
        time.sleep(0.001)  # to wait for threading
        assert self.server.got_notify
        self.server.got_notify = False

    def test_no_id(self):
        self.assertException('test_no_id', JSONRPCBadResponse, "Missing 'id'")

    def test_no_version(self):
        self.assertException('test_no_version', JSONRPCBadResponse,
                             "Missing 'jsonrpc' version")

    def test_wrong_id_retry(self):
        self.proxy._id = 1
        result = self.proxy.request('test_wrong_id_retry', 'foobar')
        assert (result == 'pass')

    def test_wrong_id_fail(self):
        self.assertException('test_wrong_id_fail', JSONRPCRequestFailure,
                             'Retries exceeded.')

    def test_bad_version(self):
        self.assertException('test_bad_version', JSONRPCBadResponse,
                             'Bad jsonrpc version. Got 9000, expects 2.0')

    def test_no_version_error(self):
        self.assertException('test_no_version_error', JSONRPCBadResponse,
                             "Missing 'jsonrpc' version")

    def test_missing_comma(self):
        self.assertException('test_missing_comma', JSONRPCBadResponse,
                             'Bad netstring: missing comma')

    def test_error_no_code(self):
        self.assertException('test_error_no_code', JSONRPCBadResponse,
                             'missing code')

    def test_error_no_message(self):
        self.assertException('test_error_no_message', JSONRPCBadResponse,
                             'missing message')

    def test_error(self):
        try:
            self.proxy.request('test_error', 'foobar')
        except JSONRPCResponseError as e:
            assert (isinstance(e, JSONRPCError))
            assert ('code' in e.value.keys())
            assert ('message' in e.value.keys())
            return
        assert False

    def test_send_request_fail(self):
        def connect(self, *args):
            raise Exception('Failed to connect.')

        self.proxy.connect = connect
        self.proxy.socket = BadSocket()
        self.assertException('test_send_request_fail', JSONRPCRequestFailure,
                             'Retries exceeded.')

    def test_send_notify_fail(self):
        def connect(self, *args):
            raise Exception('Failed to connect.')

        self.proxy.connect = connect
        self.proxy.socket = BadSocket()
        self.assertException('test_send_notify_fail', JSONRPCRequestFailure,
                             'Failed to send.', notify=True)

    def test_send_notify_retry(self):
        self.proxy.socket = BadSocket(self.proxy.socket)
        result = self.proxy.notify('test_notify', 'foobar')
        assert (result is None)
        time.sleep(0.001)  # to wait for threading
        assert self.server.got_notify
        self.server.got_notify = False
