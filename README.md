distributed_agents extends the GRPC to provide RPC calls to multiple machines at once.

Define a protobuf file that describes the agent interface, and the distributed_agents
system will generate a working client-side python agent and a server-side template python agent. 
All that is needed is for the agent developer to write the server-side python code in the 
template. Once done, an end user can use the agent to run the code on an arbitrary number
of machines. This is done using a python class. Simply call the methods and they run
on remote machines. 

For instance, to start tcpdump on two machines for 60 seconds then archive the captures using the 
python RPC interface:

```python
#!/usr/bin/env python3

import time

from tcpdump_agent import TcpDumpAgent, TcpDumpAgentException

if __name__ == '__main__':
    tcpdump_nodes = ['vrouter.smalltest.edgect', 'ct1.smalltest.edgect']

    # start/create agents.
    tcpdump = TcpDumpAgent(tcpdump_nodes)

    # configure and run tcpdump
    responses = tcpdump.Configure(dumpfile='/tmp/tcpdump.cap', agentlog='/tmp/tcpdump_agent.log')
    if not responses.success():
        print('Error configuring tcpdump: {}'.format(responses.status()))
        exit(1)

    responses = tcpdump.StartCollection(destination='traf21')
    if not responses.success():
        print('Error starting tcpdump: {}'.format(responses.status()))
        exit(2)

    time.sleep(60)

    responses = tcpdump.StopCollection()
    if not responses.success():
        print('Error stopping tcpdump: {}'.format(responses.status()))
        exit(3)

    responses = tcpdump.ArchiveDump(path='/zfs/edgelab/glawler/tcpdumps', tag='GTL')
    if not responses.success():
        print('Error archiving packet captures: {}'.format(responses.status()))
        exit(4)

    tcpdump.close() 
    exit(0)
```

Here's an example that starts Apache on servers, starts curl agents on clients to generate traffic, 
runs tcpdump on a few nodes between the clients and servers, then achives the capture files.

Note that all try/except and most error handing has been removed to make the code more easily read.

```python
#!/usr/bin/env python3

import logging
import time

from tcpdump_agent import TcpDumpAgent, TcpDumpAgentException
from http_server_agent import HttpServerAgent, HttpServerAgentException
from http_client_agent import HttpClientAgent, HttpClientAgentException

log = logging.getLogger(__name__)

if __name__ == '__main__':
    # in a real script these would be read in from a file.
    apache_nodes = [
        'traf21'
    ]
    apache_nodes_fqdn = [
        'traf21.smalltest.edgect'
    ]
    curl_nodes_fqdn = [
        'traf11.smalltest.edgect'
    ]
    tcpdump_nodes_fqdn = [
        'vrouter.smalltest.edgect',
        'ct1.smalltest.edgect'
    ]

    # start/create agents.
    apache = HttpServerAgent(apache_nodes_fqdn)
    tcpdump = TcpDumpAgent(tcpdump_nodes_fqdn)
    curl = HttpClientAgent(curl_nodes_fqdn)

    # start servers, clients, and tcpdump
    responses = apache.StartServer()
    responses = tcpdump.Configure(dumpfile='/tmp/tcpdump.cap', agentlog='/tmp/tcpdump_agent.log')
    responses = tcpdump.StartCollection(destination='traf21')
    responses = curl.StartTraffic(servers=apache_nodes)

    # let things happen
    time.sleep(600)

    # stop tcpdumps, servers, and clients. archive packet captures
    responses = tcpdump.StopCollection()
    responses = tcpdump.ArchiveDump(path='/zfs/edgelab/glawler/tcpdumps', tag='GTL')
    responses = curl.StopTraffic()
    responses = apache.StopServer()

    # clean up and exit.
    log.info('Experiment complete.')
    curl.close()
    apache.close()
    tcpdump.close()

    exit(0)
```


Here's an example of a protobuf file and what a generate client and server-template look like.

```protobuf
syntax = "proto3";

package http_client_agent;

service HttpClientAgent {
    rpc Configure(ConfigArgs) returns (Response) {}
    rpc StartTraffic(StartTrafficArgs) returns (Response) {}
    rpc StopTraffic(StopTrafficArgs) returns (Response) {}
    rpc ChangeTraffic(ChangeTrafficArgs) returns(Response) {}
}

message Response {
    bool success = 1;
    // Message about execution. Error message, status, etc.
    string comment = 2;
}

message ConfigArgs {
    // "sizes" is eval'd as python code and cast to an int. python random module can be used.
    // sizes = "1000" gives 1000 bytes per packet.
    // sizes = "random.randint(1000,2000)" gives a packet between 1000 and 2000 bytes randomly.
    string sizes = 1;
    int32 rate_limit = 2;
    bool use_socks = 3;
    string socks_server = 4; 
    int32 socks_port = 5;
    int32 socks_version = 6;
    int32 local_port = 7;
}

message StartTrafficArgs {
    repeated string servers = 1;
}

message StopTrafficArgs {

}

message ChangeTrafficArgs {
    // Can be negative or positive to decrease/increase.
    int32 stepsize = 1;
}
```

...the generated service agent (remote-side) code:

```python
import logging
import grpc

import http_client_agent_pb2 as pb
import http_client_agent_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent, DistributedAgentException
from distributed_agent import DistributedAgentResponses as Responses

log = logging.getLogger(__name__)

def AddServicer(server):
    pb_grpc.add_HttpClientAgentServicer_to_server(HttpClientAgentServicer(), server)

class HttpClientAgentServicerException(Exception):
    pass

class HttpClientAgentServicer(pb_grpc.HttpClientAgentServicer):
    def __init__(self):
        log.debug("HttpClientAgentServicer created.")
        super().__init__()

    def StopTraffic(self, request, context):
        log.debug("Invoking: StopTraffic(...)")
        # Now use the args above to do the actual work of StopTraffic.
        # Until then, return a success=False response.
        return pb.Response(success=False, comment="Not implemented.")

    def StartTraffic(self, request, context):
        log.debug("Invoking: StartTraffic(...)")
        servers = request.servers
        # Now use the args above to do the actual work of StartTraffic.
        # Until then, return a success=False response.
        return pb.Response(success=False, comment="Not implemented.")

    def Configure(self, request, context):
        log.debug("Invoking: Configure(...)")
        sizes = request.sizes
        rate_limit = request.rate_limit
        use_socks = request.use_socks
        socks_server = request.socks_server
        socks_port = request.socks_port
        socks_version = request.socks_version
        local_port = request.local_port
        # Now use the args above to do the actual work of Configure.
        # Until then, return a success=False response.
        return pb.Response(success=False, comment="Not implemented.")

    def ChangeTraffic(self, request, context):
        log.debug("Invoking: ChangeTraffic(...)")
        stepsize = request.stepsize
        # Now use the args above to do the actual work of ChangeTraffic.
        # Until then, return a success=False response.
        return pb.Response(success=False, comment="Not implemented.")
```


