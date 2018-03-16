#!/usr/bin/env python3

import logging
import time
from sys import argv

from iperf_agent import IperfAgent, IperfAgentException

log = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(threadName)s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

def _error(msg):
    log.critical(msg)
    iperf.close()
    exit(1)

if __name__ == '__main__':
    exp = 'smalltest.edgect'
    # DETER wants FQDN on the control network.
    iperf_nodes = ['{}.{}'.format(n, exp) for n in ['traf11', 'ct1', 'traf21', 'ct2']]

    # define some flows (short names are on data network. we're using iperf to generate data traffic here):
    flows = {
        'traf11': 'ct2',
        'traf21': 'ct1'
    }
    
    try: 
        # start/create agents.
        iperf = IperfAgent(iperf_nodes)

        responses = iperf.Configure(flows=flows, client_args='', logdir='/tmp', runname=None, json=False)
        if not responses.success():
            _error('Error configuring iperf: {}'.format(responses.status()))

        cmd = 'start' if len(argv) < 2 or argv[1] == 'start' else 'stop'
        if cmd == 'stop':
            responses = iperf.StopTraffic()
        else:
            responses = iperf.StartTraffic()

        if not responses.success():
            _error('Error running cmd {} on iperf: {}'.format(cmd, responses.status()))

        for node, response in iperf.Status(['ct1', 'ct2']):
            log.info('Status from {}: {}'.format(node, response))

    except IperfAgentException as e:
        _error('Exception when running: {}'.format(e))

    iperf.close()
    exit(0)
