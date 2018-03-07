import logging
import grpc

import http_client_agent_pb2 as pb
import http_client_agent_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent, DistributedAgentException
from distributed_agent import DistributedAgentResponses as Responses

log = logging.getLogger(__name__)

class HttpClientAgentException(Exception):
    pass

class HttpClientAgent(DistributedAgent):
    def __init__(self, nodes, port=51000):
        super().__init__(nodes, port)
        self.load_agent('HttpClientAgent', pb_grpc.HttpClientAgentStub)

    def StartTraffic(self, **kwargs):
        return self.blocking_call('StartTraffic', pb.StartTrafficArgs(**kwargs))

    def StopTraffic(self, **kwargs):
        return self.blocking_call('StopTraffic', pb.StopTrafficArgs(**kwargs))

    def Configure(self, **kwargs):
        return self.blocking_call('Configure', pb.ConfigArgs(**kwargs))
