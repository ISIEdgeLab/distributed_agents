#!/usr/bin/env python3

import logging
import argparse
import time

from iperf_agent import IperfAgent, IperfAgentException

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Control iperf instances on remote machines.')
    parser.add_argument('-f', '--flow', dest='flows', type=str, required=True, action='append', 
                        help='Flow of the form "server:client".')
    parser.add_argument('-p', '--port', type=int, help='Port the agent is listening on.', default=51000)
    args = parser.parse_args()

    port = args.port

    # find all nodes.
    nodes = set()
    for flow in args.flows:
        s, c = flow.split(':')
        nodes.add(s)
        nodes.add(c)

    nodes = list(nodes)

    try:
        # initialize all agents in the group.
        agent = IperfAgent(nodes)

        responses = agent.start_flows(args.flows)
        if not all(responses):
            log.critical('error while starting flows.')
            exit(1)

    except IperfAgentException as e:
        log.critical(e)
        exit(2)


