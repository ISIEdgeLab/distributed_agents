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
        print('Error configuring tpcdump: {}'.format(responses.status()))
        exit(1)

    responses = tcpdump.StartCollection(destination='traf21')
    if not responses.success():
        print('Error starting tpcdump: {}'.format(responses.status()))
        exit(2)

    time.sleep(60)

    responses = tcpdump.StopCollection()
    if not responses.success():
        print('Error stopping tpcdump: {}'.format(responses.status()))
        exit(3)

    responses = tcpdump.ArchiveDump(path='/zfs/edgelab/glawler/tcpdumps', tag='GTL')
    if not responses.success():
        print('Error archiving packet captures: {}'.format(responses.status()))
        exit(4)

    exit(0)
```
