#!/usr/bin/env python3

import logging
import time

from tcpdump_agent import TcpDumpAgent, TcpDumpAgentException
from http_server_agent import HttpServerAgent, HttpServerAgentException
from distributed_agent import DistributedAgentException

log = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(threadName)s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    exit_val = 0
    exp = 'smalltest.edgect'
    apache_nodes = ['traf21.{}'.format(exp)]
    tcpdump_nodes = ['vrouter.{}'.format(exp), 'ct1.{}'.format(exp)]

    try: 
        # start/create agents.
        apache = HttpServerAgent(apache_nodes)
        tcpdump = TcpDumpAgent(tcpdump_nodes)

        # start apache
        apache.StartServer()

        # configure and run tcpdump
        tcpdump.Configure('/tmp/tcpdump.cap', '/tmp/tcpdump_agent.log')
        tcpdump.StartCollection(destination='traf21')

        sleep_time = 10
        log.info('Collecting for {} seconds.'.format(sleep_time))
        time.sleep(sleep_time)

        tcpdump.StopCollection()
        tcpdump.ArchiveDump('/zfs/edgelab/glawler/tcpdumps', filename=None, tag='GTL')

        # stop apache.
        apache.StopServer()

    except DistributedAgentException as e:
        log.critical(e)
        exit_val = 1

    log.info('Experiment complete.')
    apache.close()
    tcpdump.close()
    exit(exit_val)
