""" Client part of optimization frameworks interaction. """

import socket
import json
import logging
import threading
import selectors

from queue import Queue, Empty
from hashlib import sha256

from .errors import OptimizerServerError


SERVER_SUPPORTED_ALGORITHMS = [
    # Bayesian optimization
    'TSEMO',  # Multi Objective ONLY
    'SOBO',  # Single Objective
    'MTBO',  # Multi-task Bayesian optimization
    'ENTMOOT',  # Ensemble Tree Model Optimization
    # Local search
    'NelderMead',  # Simplex
    # Global search
    'SNOBFIT',
]

DEFAULT_HOST = 'dragonsoop2.chem.gla.ac.uk'
DEFAULT_PORT = 12111
DEFAULT_TIMEOUT = 60 # seconds
DEFAULT_BUFFER_SIZE = 4096
STANDARD_ENCODING = 'ascii'
NUM_RETRIES_FOR_RECEIVE = 60


def proc_data(proc_hash, parameters, result=None, target=None, batch_size=1):
    """ Helper function to forge data dictionary for the optimizer client. """
    data_msg = {
        'hash': proc_hash,
        'parameters': parameters
    }
    if result:
        data_msg.update(result=result)
    if target:
        data_msg.update(target=target)
    data_msg.update(batch_size=batch_size)

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

        # try:
        #     self.client.connect((DEFAULT_HOST, DEFAULT_PORT))
        #     self.client.setblocking(False)
        #     self.selector.register(self.client, selectors.EVENT_READ)
        #     self.receiver_thread.start()
        # except socket.gaierror:
        #     raise ConnectionError('Wrong host address') from None
        # except ConnectionRefusedError:
        #     raise ConnectionError('Optimizer server is not running') from None

        # self.logger.info('Connection opened')

    def initialize(self, init_data):
        """ Initializing algorithm on a server side. """

        self.logger.info('Initializing server algorithm.')
        self._send(init_data)
        reply = self._receive()
        try:
            assert 'exception' not in reply
            self.logger.info(
                'Initialized algorithm %s', reply['strategy']['name'])
            return reply['strategy']

        except AssertionError:
            raise OptimizerServerError(
                f'Exception returned from server:\n{reply["exception"]}'
            ) from None

        except KeyError:
            # TODO change server to send strategy every time
            pass

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
                            self.logger.info('Server closed the connection')
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
        self.reply_queue.put(
            json.dumps({'exception': 'Server disconnected'}).encode()
        )

    def _receive(self):
        """ High level method to receive messages from server. """

        # One hour should be sufficient for any algorithm to calculate
        for _ in range(NUM_RETRIES_FOR_RECEIVE):
            try:
                reply = self.reply_queue.get(timeout=DEFAULT_TIMEOUT)
                break
            except Empty:
                self.logger.info('No reply received within %d seconds, \
retrying', DEFAULT_TIMEOUT)

        # decoding
        reply = json.loads(reply.decode(STANDARD_ENCODING))

        return reply

    def query(self, data):
        """ Query new data from server. """
        print(data)
        self._send(data)
        new_data = self._receive()

        return new_data

    def disconnect(self):
        """ Close and unregister client socket, join listening thread. """
        self.logger.info("Closing")
        self.client.close()
        self.receiver_thread.join()
        self.logger.info('Listening thread closed.')
