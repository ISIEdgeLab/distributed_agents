import logging
import grpc

import http_server_agent_pb2 as pb
import http_server_agent_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent

log = logging.getLogger(__name__)

class HttpServerAgentException(Exception):
    pass

class HttpServerAgent(DistributedAgent):
    def __init__(self, nodes, port=51000):
        super().__init__(nodes, port)
        self.load_agent('HttpServerAgent', pb_grpc.HttpServerAgentStub)

    def StartServer(self):
        return self.blocking_call('StartServer', pb.StopServerArgs())

    def StopServer(self):
        return self.blocking_call('StopServer', pb.StopServerArgs())
