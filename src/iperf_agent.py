import logging

import iperf_agent_pb2
import iperf_agent_pb2_grpc

from distributed_agent import DistributedAgent, DistributedAgentException

log = logging.getLogger(__name__)

class IperfAgentException(Exception):
    pass

class IperfAgent(DistributedAgentException):
    def __init__(self, nodes, port=51000):
        super(DistributedAgentException, self).__init__(nodes, port)
        self.load_agent('IperfAgent', iperf_agent_pb2_grpc.py.IperfAgentStub)

    def start_flows(self, flows):
        '''Start flows on servers and clients. Returns a list of bools returned by each agent.'''
        responses = []
        for f in flows:
            s, c = f.split(':')

            for n in [s, c]:   # init and sanity check
                if not n in self._agents:
                    raise IperfAgentException('flow node {} not an Iperf Agent.'.format(n))

            # start server, then start client.
            resp = self._agents[s].StartServer(iperf_agent_pb2.ServerStartArgs(tcp=True))
            responses.append(resp.success)

            resp = self._agents[c].StartClient(iperf_agent_pb2.ClientStartArgs(server=s, tcp=True))
            responses.append(resp.success)

        return responses
