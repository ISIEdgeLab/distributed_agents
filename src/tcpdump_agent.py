import logging
import grpc

import tcpdump_agent_pb2 as pb
import tcpdump_agent_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent, DistributedAgentException
from distributed_agent import DistributedAgentResponses as Responses

log = logging.getLogger(__name__)

def _response_to_dict(resp):
    return {'success': resp.success, 'comment': resp.comment}

class TcpDumpAgentException(Exception):
    pass

class TcpDumpAgent(DistributedAgent):
    def __init__(self, nodes, port=51000):
        super().__init__(nodes, port)
        self.load_agent('TcpDumpAgent', pb_grpc.TcpDumpAgentStub)

    def Configure(self, **kwargs):
        return self.blocking_call('Configure', pb.Config(**kwargs))

    def StartCollection(self, **kwargs):
        return self.blocking_call('StartCollection', pb.StartArgs(**kwargs))

    def StopCollection(self, **kwargs):
        return self.blocking_call('StopCollection', pb.StopArgs(**kwargs))

    def ArchiveDump(self, **kwargs):
        return self.blocking_call('ArchiveDump', pb.ArchiveArgs(**kwargs))
