#!/usr/bin/env python3

import logging
import time

from tcpdump_agent import TcpDumpAgent, TcpDumpAgentException

log = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(threadName)s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

def exit_with_msg(msg, agent, resps):
    log.critical('{}: {}'.format(msg, resps.status()))
    agent.close()
    exit(1)

if __name__ == '__main__':
    nodes = ['vrouter.smalltest.edgect', 'ct1.smalltest.edgect']
    try:
        agent = TcpDumpAgent(nodes)
        responses = agent.Configure('/tmp/tcpdump.cap', '/tmp/tcpdump_agent.log')
        if not responses.success():
            exit_with_msg('Error configuring', agent, responses)

        responses = agent.StartCollection(destination='traf21')
        if not responses.success():
            exit_with_msg('Error starting collection', agent, responses)

        sleep_time = 10
        log.info('Collecting for {} seconds.'.format(sleep_time))
        time.sleep(sleep_time)

        responses = agent.StopCollection()
        if not responses.success():
            exit_with_msg('Error stopping collection', agent, responses)

        responses = agent.ArchiveDump('/zfs/edgelab/glawler/tcpdumps', filename=None, tag='GTL')
        if not responses.success():
            exit_with_msg('Error stopping collection', agent, responses)

    except TcpDumpAgentException as e:
        log.critical(e)
        agent.close()
        exit(1)

    agent.close()
    exit(0)
