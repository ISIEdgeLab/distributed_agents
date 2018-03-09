distributed_agents extends the GRPC to provide RPC calls to multiple machines at once.

For instance to start tcpdump on two machines for 60 seconds then archive the captures using the 
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
