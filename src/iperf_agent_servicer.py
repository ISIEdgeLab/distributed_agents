from concurrent import futures
import logging
import time

import grpc
import iperf_agent_pb2 as pb
import iperf_agent_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class IperfAgentServicer(pb_grpc.IperfAgentServicer):
    def __init__(self):
        log.debug('IperfAgentServicer created.')
        pass

    def StartServer(self, request, context):
        log.info('Starting iperf server with args: {}'.format(request))
        return pb.AgentResponse(success=True)

    def StopServer(self, request, context):
        log.info('Stopping iperf server.')
        return pb.AgentResponse(success=True)

    def StartClient(self, request, context):
        log.info('Starting iperf client with args: {}'.format(request))
        return pb.AgentResponse(success=True)

    def StopClient(self, request, context):
        log.info('Stopping iperf client.')
        return pb.AgentResponse(success=True)

# Add instance of this agent to ther server.
def AddServicer(server):
    pb_grpc.add_IperfAgentServicer_to_server(IperfAgentServicer(), server)
