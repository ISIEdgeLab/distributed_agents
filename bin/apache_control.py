#!/usr/bin/env python3

import logging
import time
from sys import argv

from dgrpc.http_server_agent import HttpServerAgent, HttpServerAgentException

log = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(threadName)s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    exp = 'smalltest.edgect'
    apache_nodes = ['traf21']
    apache_nodes_fqdn = ['{}.{}'.format(n, exp) for n in apache_nodes]

    # start/create agents.
    apache = HttpServerAgent(apache_nodes_fqdn)

    if argv[1] == 'stop':
        responses = apache.StopServer()
    else:
        responses = apache.StartServer()

    if not responses.success():
        msg = 'Error starting apache: {}'.format(responses.status())
        log.critical(msg)
        apache.close()
        exit(1)

    apache.close()
    exit(0)
