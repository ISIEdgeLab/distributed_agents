import logging
import grpc
import sys
from concurrent import futures

sys.path.append('./pb')  # GTL ugh.
import agent_server_pb2_grpc as pb_grpc
import agent_server_pb2 as pb

log = logging.getLogger(__name__)

class DistributedAgentException(Exception):
    pass

class DistributedAgent:
    def __init__(self, nodes, port):
        self.port = port
        self.nodes = nodes

        self.channels = {}
        self.agents = {}
        self.server_agents = {}

    def load_agent(self, name, agent_stub):
        '''Takes a reference to a agent stub (client stub) class and creates channels to all 
        referenced nodes, creating instances of that class in self.agents{}. Also loads the
        agent's servicer in the remote daemon and installes the agent dependencies.'''

        # open all channels, create agent_server client-side stubs, and Load() the agent on the server.
        log.info('Loading {}'.format(name))
        try:
            load_calls = {}
            with futures.ThreadPoolExecutor(len(self.nodes)) as fte:
                for n in self.nodes:
                    if not n in self.channels:
                        self.channels[n] = grpc.insecure_channel('{}:{}'.format(n, self.port))
                        self.server_agents[n] = pb_grpc.AgentServerStub(self.channels[n])
                        
                        # submit calls to Load the server-soide agent to the future.
                        # The future call maps to the node name.
                        load_calls[fte.submit(self.server_agents[n].Load, pb.AgentConfig(name=name))] = n

                for f in futures.as_completed(load_calls):
                    n = load_calls[f]
                    response = f.result()
                    if not response.success:
                        raise DistributedAgentException(
                            'Error loading {} on node {}: {}'.format(name, n, response.comment))

        # GTL TODO: figure out what the proper thing to catch here is.
        except Exception as e:
            msg = 'Error: {}'.format(e)
            log.critical(msg)
            raise DistributedAgentException(msg)

        # Now that the agents are loaded remotely create the client-side stub agent we'll use 
        # to talk to the server-side agent.
        try:
            for n in self.nodes:
                self.agents[n] = agent_stub(self.channels[n])
        except Exception as e:
            msg = 'Error creating agent client stub: {}'.format(e)
            log.critical(msg)
            raise DistributedAgentException(msg)

        log.info('Loaded {} (server-side) on {}'.format(name, ', '.join(self.nodes)))

    def close(self):
        '''Cleanup and close any existing agents.'''
        # see https://github.com/grpc/grpc/issues/11804
        # bug in grpc which doesn't cleanup on exit() properly. 
        for node, agent in self.agents.items():
            del agent
            self.agents[node] = None

        for node, channel in self.channels.items():
            del channel
            self.channels[node] = None

    def blocking_call(self, method, args):
        '''
            Call the given method with the given args for each agent in turn. Return all response once
            all agents have responded.
                arg method is a string that is the method to call.
                arg args is a protbuf class instance that holds the args.

            Calls to all nodes will happend concurrently. 
            blocking_call will only return once all nodes have responded.
        '''
        responses = DistributedAgentResponses()
        future_responses = {}
        calls = {}
        with futures.ThreadPoolExecutor(len(self.agents)) as tpe:
            for node, agent in self.agents.items():
                func = getattr(agent, method, None)
                if not func:
                    raise DistributedAgentException('No such method {} in agent {}.'.format(method, agent))
                
                log.debug('On node {}, calling: {}(...)'.format(node, method))
                calls[tpe.submit(func, args)] = node

            for f in futures.as_completed(calls):
                try: 
                    node = calls[f]
                    r = f.result()
                except grpc.RpcError as e:
                    # I'm not sure when this gets raised when using a thread pool executor...
                    log.critical('RPC error: {}'.format(e))
                    raise DistributedAgentException(e)

                comment = '' if not r.comment else ': {}'.format(r.comment)
                log.debug('{}: {}() --> {}{}'.format(node.split('.')[0], method, r.success, comment))
                responses.add(node, r)

        return responses

    def blocking_call_server_streaming(self, method, args):
        '''Much like blocking_call, but yields responses when they happen. Should only be invoked on 
        agent methods that return a stream of things.

        Note that the implementation is still sequential, so the order of return will be the order
        of agents. Calls do not happen in parallel (yet). 
        '''
        for node, agent in self.agents.items():
            responses = DistributedAgentResponses()
            try:
                func = getattr(agent, method, None)
                if not func:
                    raise DistributedAgentException('No such method {} in agent {}.'.format(method, agent))
                
                log.debug('On node {}, calling: {}(...)'.format(node, method))
                for r in func(args):
                    log.debug('stream response: {} ({})'.format(r, type(r)))
                    yield r
            except grpc.RpcError as e:
                log.critical('RPC error: {}'.format(e))
                raise DistributedAgentException(e)
            
            # comment = '' if not r.comment else ': {}'.format(r.comment)
            # log.debug('{}: {}() --> {}{}'.format(node.split('.')[0], method, r.success, comment))

            # responses.add(node, r)
            # yield responses
        # return None

'''Aux class that exists simply as a shim between protobuffer classes and python. It will mirror exactly
the protobuf Response data.'''
class DistributedAgentResponse(): 
    def __init__(self, pbresp):
        # GTL TODO - figure out a smart way to copy instance variables without naming them speciffically.
        self.success = pbresp.success
        self.comment = pbresp.comment

'''This is a dict of responses indexed by host with a few util methods added.'''
class DistributedAgentResponses:
    def __init__(self):
        self._responses = {}

    def add(self, host, resp):
        '''Add this response from this host. Will overwrite host's entry if it exists.'''
        self._responses[host] = DistributedAgentResponse(resp)

    def success(self):
        for k, v in self._responses.items():
            if not v.success:
                return False

        return True

    def status(self):
        '''Return string suitable for logging/printing based on responses.'''
        if self.success():
            return "SUCCESS: All nodes."

        failed = ['{}={}'.format(node, vs.success) for node, vs in self._responses.items() if not vs.success]
        return 'FAILED: {}'.format(', '.join(failed))
