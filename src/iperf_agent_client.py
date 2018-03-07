import logging
import argparse
import time

import grpc

import iperf_agent_pb2
import iperf_agent_pb2_grpc

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Control iperf instances on remote machines.')
    parser.add_argument('-f', '--flow', dest='flows', type=str, required=True, action='append', 
                        help='Flow of the form "server:client".')
    parser.add_argument('-p', '--port', type=int, help='Port the agent is listening on.', default=51000)
    args = parser.parse_args()

    port = args.port

    channels = []
    servers, clients = [], []
    for flow in args.flows:
        s, c = flow.split(':')
        if not s in channels:
            chan = rpc.insecure_channel('{}.{}'.format(s, port))
            log.info('Conected to {}'.format(s))
            servers.append(iperf_agent_pb2_grpc.IperfServerStub(chan))

        if not c in channels:
            chan = rpc.insecure_channel('{}.{}'.format(c, port))
            log.info('Conected to {}'.format(c))
            clients.append(iperf_agent_pb2_grpc.IperfClientStub(chan))

    log.info('Starting servers.')
    for s in servers:
        resp = s.Start(iperf_agent_pb2.ServerStartArgs(tcp=True))
        log.info('Server started: {}'.format(resp))

    log.info('Starting clients.')
    for c in clients:
        resp = c.Start(iperf_agent_pb2.ClientStartArgs(server=serv, tcp=True))
        log.info('Client started: {}'.format(resp))

    try:
        while True:
            log.debug('...sleeping.')
            time.sleep(60*60*24)
    except KeyboardInterrupt:
        pass

    log.info('Stopping client.')
    cli_agent.Stop(iperf_agent_pb2.ClientStopArgs())

    log.info('Stopping server.')
    serv_agent.Stop(iperf_agent_pb2.ServerStopArgs())

    exit(0)
