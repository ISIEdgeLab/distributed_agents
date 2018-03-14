#!/usr/bin/env python3

import logging
import time

from tcpdump_agent import TcpdumpAgent, TcpdumpAgentException
from http_server_agent import HttpServerAgent, HttpServerAgentException
from http_client_agent import HttpClientAgent, HttpClientAgentException

log = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(threadName)s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    exp = 'smalltest.edgect'
    apache_nodes = ['traf21']
    apache_nodes_fqdn = ['{}.{}'.format(n, exp) for n in apache_nodes]
    curl_nodes_fqdn = ['traf11.{}'.format(exp)]
    tcpdump_nodes_fqdn = ['vrouter.{}'.format(exp), 'ct1.{}'.format(exp)]

    # start/create agents.
    apache = HttpServerAgent(apache_nodes_fqdn)
    tcpdump = TcpdumpAgent(tcpdump_nodes_fqdn)
    curl = HttpClientAgent(curl_nodes_fqdn)

    def clean_and_exit(msg):
        log.critical(msg)
        apache.close()
        tcpdump.close()
        curl.close()
        exit(1)

    # start apache
    responses = apache.StartServer()
    if not responses.success():
        clean_and_exit('Error starting apache: {}'.format(responses.status()))

    # configure and run tcpdump
    responses = tcpdump.Configure(dumpfile='/tmp/tcpdump.cap', agentlog='/tmp/tcpdump_agent.log')
    if not responses.success():
        clean_and_exit('Error configuring tcpdump: {}'.format(responses.status()))

    responses = tcpdump.StartCollection(destination='traf21')
    if not responses.success():
        clean_and_exit('Error starting tcpdump collection: {}'.format(responses.status()))

    # start curl agents. (Use default configuration.)
    responses = curl.StartTraffic(servers=apache_nodes)
    if not responses.success():
        clean_and_exit('Error starting traffic on curl clients.')

    sleep_time = 10
    log.info('Collecting for {} seconds.'.format(sleep_time))
    time.sleep(sleep_time)

    responses = tcpdump.StopCollection()
    if not responses.success():
        clean_and_exit('Error stopping tcpdump collection: {}'.format(responses.status()))

    responses = tcpdump.ArchiveDump(path='/zfs/edgelab/glawler/tcpdumps', tag='GTL')
    if not responses.success():
        clean_and_exit('Error archiving tcpdump packet files: {}'.format(responses.status()))

    # stop curl.
    responses = curl.StopTraffic()
    if not responses.success():
        clean_and_exit('Error stopping curl clients: {}'.format(responses.status()))

    # stop apache.
    responses = apache.StopServer()
    if not responses.success():
        clean_and_exit('Error stoping apache: {}'.format(responses.status()))

    log.info('Experiment complete.')
    curl.close()
    apache.close()
    tcpdump.close()
    exit(0)
