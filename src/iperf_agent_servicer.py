
#
# This file generated from a proto file. You can edit it, but it may 
# get overwritten. This file assumes that you've created standard python 
# grpc stub ans servicer files from the same proto files.
#

import logging
import grpc
import sys
import os
import stat

from socket import gethostname
from time import gmtime, strftime, sleep
from subprocess import CalledProcessError, Popen, STDOUT, call

sys.path.append('./pb')  # GTL: Ugh. Find a better way to do this.

import iperf_agent_pb2 as pb
import iperf_agent_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

def AddServicer(server):
    pb_grpc.add_IperfAgentServicer_to_server(IperfAgentServicer(), server)

class IperfAgentServicerException(Exception):
    pass

class IperfAgentServicer(pb_grpc.IperfAgentServicer):
    def __init__(self):
        log.debug("IperfAgentServicer created.")
        super().__init__()
        # A flow is a list of client->server pairs:
        # ex: 
        #   self.flows = [
        #                   {'client': 'foo' 'server': 'baz'}, 
        #                   {'client': 'bar' 'server': 'koala'}, 
        #                ]
        self.flows = None
        self.client_args = ''
        self.logdir = os.path.join('/', 'tmp', 'iperf')
        self.runname = ''       # include this in log file name if given.
        self.json = True        # if True, output json logs instead of text.

        # do not touch below here.
        self._proc = {}
        self._isrunning = False
        self._logfd = None

        self._loglevel = 'info'
        self._nodename = gethostname().split('.', maxsplit=1)[0]

    # returns pb.Response(success=success, comment=comment)
    def Configure(self, request, context):
        log.debug("Invoking: Configure(...)")
        self.flows = request.flows
        self.client_args = request.client_args
        self.logdir = request.logdir
        self.runname = request.runname
        self.json = request.json

        log.info('Configuration: ')
        for c in [
                (self.flows, 'flows'),
                (self.client_args, 'client_args'), 
                (self.logdir, 'logdir'),
                (self.runname, 'runname'),
                (self.json, 'json')]:
            log.info('{} ({}): {}'.format(c[1], type(c[0]), c[0]))

        success = self._confirm_configuration()
        return pb.Response(success=success, comment='')

    # returns pb.Response(success=success, comment=comment)
    def StartTraffic(self, request, context):
        '''Start iperf everywhere.'''
        log.debug("Invoking: StartTraffic(...)")
        if self._proc:
            log.info('Stopping older iperf3 process.')
            self.StopTraffic(None, None)
            
        for client, server in self.flows.items():
            cmd = None
            if server == self._nodename:
                cmd = 'iperf3 -s '
            elif client == self._nodename:
                cmd = 'iperf3 -c {} {}'.format(server, self.client_args)

            # iperf3 does not handle io buffering correctly, but it does seem to when --verbose
            # is given. If we leave this out, we will frequently not capture all lines in the log
            # file. 
            if cmd:
                cmd += ' --verbose'

                if self.json:
                    cmd += ' -J'

            if cmd:
                # try a few times in case teh servers have not started.
                count = 5
                while count:
                    try:
                        log.info('running iperf as: "{}"'.format(cmd))
                        fd = self._get_logfd()
                        self._proc = Popen(cmd.split(), stdout=fd, stderr=STDOUT, close_fds=True)
                    except CalledProcessError as e:
                        log.error('Unable to start iperf process: {}'.format(e))
                        self._clear_logfd()
                        self._proc = None
                  
                    if self._proc:
                        sleep(1)    # let it fail or no.
                        if None == self._proc.poll():   # poll() returns None if proc running else exit value.
                            log.info('Error starting iperf. Trying again.')
                        else:
                             break

                    log.info('Unable to start iperf trying again in a few seconds....')
                    count = count-1
                    sleep(1)

                log.info('iperf started')
                break

        success = self._proc != None

        return pb.Response(success=success, comment='')

    # returns pb.Response(success=success, comment=comment)
    def StopTraffic(self, request, context):
        log.debug("Invoking: StopTraffic(...)")
        if self._proc and not self._proc.poll():
            try:
                log.info('killing iperf3')
                self._proc.kill()
            except OSError:
                pass   # meh.

        self._clear_logfd()
        self._proc = None

        # Just to be safe. 
        try:
            log.info('pkilling iperf3')
            call('pkill iperf3'.split(), shell=True)
        except CalledProcessError as e:
            log.info('error pkilling iperf: {}'.format(e))
            pass

        return pb.Response(success=True, comment='iperf stopped')

    # returns pb.StatusResponse(success=success, comment=comment, transfer=transfer, 
    #                           bandwidth=bandwidth, retries=retries)
    def Status(self, request, context):
        log.debug("Invoking: Status(...)")
        hosts = request.hosts

        while self._proc:
            count = 0
            if self._nodename in hosts:
                # fake it until you make it.
                count += 1
                yield pb.Response(
                    success=True,
                    comment='status at <timestamp>: foo/bar/baz',
                    transfer='200ms',
                    bandwidth='not that great',
                    retries=count
                )
            # sleep(1)

        yield  pb.StatusArgs(success=False, comment='No iperf process running.')

    def _confirm_configuration(self):
        log.info('Checking given configuration...')
        if not self.logdir:
            log.critical('Logdir not set, unable to continue.')
            return False

        if not self.flows:
            log.critical('No flows given, unable to continue.')
            return False

        if not os.path.isdir(self.logdir):
            log.info('{} not found, creating it.'.format(self.logdir))
            try:
                os.mkdir(self.logdir)
                os.chmod(self.logdir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH)
            except (OSError, IOError) as e:
                log.critical('Unable to create {}: {}'.format(self.logdir, e))
                return False
       
        # python v3.2+ we would not need to do this.
        levelmap = {'debug': logging.DEBUG, 'info': logging.INFO,
                    'warning': logging.WARNING, 'error': logging.ERROR,
                    'critical': logging.CRITICAL}
        if not self._loglevel.lower() in levelmap.keys():
            log.warning('I do not know how to set log level {}'.format(
                self._loglevel))
            return FALSE

        log.setLevel(levelmap[self._loglevel.lower()])

        return True

    def _get_logfd(self):
        if not self._logfd:
            # append _ to runname if there. 
            runname = '{}_'.format(self.runname) if self.runname else ''
            filename = os.path.join(self.logdir, '{}_{}{}_iperf.log'.format(
                strftime("%Y%m%d_%H%M%S", gmtime()),
                runname,
                self._nodename))
            self._logfd = open(filename, 'w')

        return self._logfd

    def _clear_logfd(self):
        if self._logfd:
            self._logfd.close()
            self._logfd = None

