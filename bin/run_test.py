#!/usr/bin/env python3

import logging
import time

from tcpdump_agent import TcpDumpAgent, TcpDumpAgentException
from http_server_agent import HttpServerAgent, HttpServerAgentException

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

    exp = 'smalltest.edgect'

    # start apache on traf21
    try:
        apache = HttpServerAgent(['traf21.{}'.format(exp)])
        responses = apache.StartServer()
        if not responses.success():
            exit_with_msg('Error configuring', agent, responses)
    
    except HttpServerAgentException as e:
        log.critical(e)
        apache.close()
        exit(1)

    # start tcpdump on vrouter and ct1
    nodes = ['vrouter.{}'.format(exp), 'ct1.{}'.format(exp)]
    try:
        tcpdump_agent = TcpDumpAgent(nodes)
        responses = tcpdump_agent.Configure('/tmp/tcpdump.cap', '/tmp/tcpdump_agent.log')
        if not responses.success():
            exit_with_msg('Error configuring', tcpdump_agent, responses)

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

    # stop apache.
    apache.StopServer()

    agent.close()
    exit(0)
