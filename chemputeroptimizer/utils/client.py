""" Client part of optimization frameworks interaction. """

import socket
import json
import logging
import threading
import selectors

from queue import Queue, Empty
from hashlib import sha256


SERVER_SUPPORTED_ALGORITHMS = [
    'SOBO',
    'NelderMead',
    'SNOBFIT',
]

DEFAULT_HOST = 'dragonsoop2.chem.gla.ac.uk'
DEFAULT_PORT = 12111
DEFAULT_TIMEOUT = 60 # seconds
DEFAULT_BUFFER_SIZE = 4096
STANDARD_ENCODING = 'ascii'


def proc_data(proc_hash, parameters, result=None, target=None):
    """ Helper function to forge data dictionary for the optimizer client. """
    data_msg = {
        'hash': proc_hash,
        'parameters': parameters
    }
    if result:
        data_msg.update(result=result)
    if target:
        data_msg.update(target=target)
    return data_msg

def calculate_procedure_hash(procedure: str) -> str:
    """ Calculate procedure hash using sha256 algorithm.

    Args:
        procedure (str): XDL procedure as a string.

    Returns:
        str: Hash digest value as a string of hexadecimal digits.
    """
    # TODO Clean up the procedure from optimization parameters
    # To allow several procedures with different starting points to match.
    return sha256(procedure.encode('utf-8')).hexdigest()

class OptimizerClient:
    """ Client part of the optimization framework interaction. """

    def __init__(self):

        self.logger = logging.getLogger('optimizer.client')

        self.selector = selectors.DefaultSelector()
        self.client = socket.socket()
        self.reply_queue = Queue()
        self.receiver_thread = threading.Thread(
            target=self.receiver,
            name='optimizer_client_receiver_thread'
        )

        self.logger.info('Optimizer client initialized.')

        self.open_connection()

    def open_connection(self):
        """
        Opens connection and registers client socket in default selector.
        """

        try:
            self.client.connect((DEFAULT_HOST, DEFAULT_PORT))
            self.client.setblocking(False)
            self.selector.register(self.client, selectors.EVENT_READ)
            self.receiver_thread.start()
        except socket.gaierror:
            raise ConnectionError('Wrong host address') from None
        except ConnectionRefusedError:
            raise ConnectionError('Optimizer server is not running') from None

        self.logger.info('Connection opened')

    def initialize(self, init_data):
        """ Initializing algorithm on a server side. """

        self.logger.info('Initializing server algorithm.')
        self._send(init_data)
        reply = self._receive()
        self.logger.info('Initialized algorithm %s', reply['strategy']['name'])

    def _send(self, data):
        """ High level method to send messages to server. """
        # encoding
        msg = json.dumps(data).encode(STANDARD_ENCODING)
        # print(json.dumps(data, indent=4))

        # sending
        try:
            self.client.send(msg)
            self.logger.debug('Message sent %s', data)
        except Exception as e:
            raise e

    def receiver(self):
        """
        Background threading method to receive messages from socket client.
        """

        self.logger.info('Start receiving')

        while True:
            try:
                events = self.selector.select()
                for key, _ in events:
                    self.logger.debug('Client ready to read')
                    reply = b''
                    try:
                        chunk = key.fileobj.recv(DEFAULT_BUFFER_SIZE)
                        if not chunk:
                            self.logger.debug('No message received')
                            key.fileobj.close()
                            self.selector.unregister(key.fileobj)
                            break
                        self.logger.debug('Incoming message, reading')
                        while chunk:
                            self.logger.debug('Chunk received: %s',
                                              chunk.decode())
                            reply += chunk
                            chunk = key.fileobj.recv(DEFAULT_BUFFER_SIZE)
                    except BlockingIOError:
                        self.logger.debug('Forged reply: %s', reply.decode())
                        self.reply_queue.put(reply)
            except OSError:
                break

        self.logger.info('Exiting listening thread.')

    def _receive(self):
        """ High level method to receive messages from server. """
        # receiving
        try:
            reply = self.reply_queue.get(timeout=DEFAULT_TIMEOUT)
        except Empty:
            self.logger.error('No reply received within %d seconds',
                              DEFAULT_TIMEOUT)
            reply = b'{"exception": "No reply received from server"}'

        # decoding
        reply = json.loads(reply.decode(STANDARD_ENCODING))

        return reply

    def query(self, data):
        """ Query new data from server. """
        self._send(data)
        new_data = self._receive()

        return new_data

    def disconnect(self):
        """ Close and unregister client socket, join listening thread. """
        self.logger.info("Closing")
        self.client.close()
        self.receiver_thread.join()
        self.logger.info('Listening thread closed.')
