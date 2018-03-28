import logging
from os.path import exists, isdir, basename, join as path_join
from os import makedirs
from time import sleep, strftime
from shutil import copyfile
from subprocess import Popen, STDOUT, check_output, CalledProcessError
from netifaces import interfaces, ifaddresses
from socket import AF_INET, gethostbyname, gethostname

from . import tcpdump_agent_pb2 as pb
from . import tcpdump_agent_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

# Add instance of this agent to the server.
def AddServicer(server):
    pb_grpc.add_TcpdumpAgentServicer_to_server(TcpdumpAgentServicer(), server)

class TcpdumpAgentServicer(pb_grpc.TcpdumpAgentServicer):
    def __init__(self):
        log.debug('TcpdumpAgentServicer created.')

        self.dumpfile = path_join('/', 'tmp', 'tcpdump.cap')
        self.agentlog = path_join('/', 'tmp', 'tcpdump_agent.log')

        self._proc = None
        self._lfile = None

    def Configure(self, request, context):
        self.dumpfile = request.dumpfile
        self.agentlog = request.agentlog
        log.info('configured: dumpfile: {}, agentlog: {}'.format(self.dumpfile, self.agentlog))
        return pb.Response(success=True, comment="")

    def StartCollection(self, request, context):
        return self._start_collection(
            request.expression,
            request.destination,
            request.dump_args,
            request.capture_address
        )

    def StopCollection(self, request, context):
        return self._stop_collection(
            request.force
        )

    def ArchiveDump(self, request, context):
        return self._archive_dump(request.path, request.filename, request.tag)

    def Status(self, request, context):
        return pb.Response(success=True, comment="")

    def _start_collection(self, expression=None, destination=None, dump_args=None, capture_address=None):
        if self._proc:
            log.info('tcpdump already running. Stopping it so we can restart it...')
            self._stop_collection(force=True)

        log.info("starting collection")
        cmd = 'tcpdump'

        if destination:
            iface = self._dest2iface(destination)
            if not iface:
                msg = 'Unable to discover interface that routes to {}.'.format(destination)
                log.critical(msg)
                return pb.Response(success=False, comment=msg)

            cmd += ' -i {}'.format(iface)

        elif capture_address:
            iface = self._addr2iface(capture_address)
            if not iface:
                msg = 'Unable to find iface for address: {}'.format(capture_address)
                log.critical(msg)
                return pb.Response(success=False, comment=msg)

            cmd += ' -i {}'.format(iface) 

        else:
            cmd += ' -i any'

        cmd += ' -w {}'.format(self.dumpfile)
    
        if dump_args:
            cmd += ' {}'.format(dump_args)

        cmd += ' {}'.format(expression)

        log.info('running: {}'.format(cmd))

        # Do not remove the stdout, stderr redirection! It turns out tcpdump really doesn't
        # like not having a stdout/err and will die if this is removed.
        self._lfile = open(self.agentlog, 'w')
        try:
            self._proc = Popen(cmd.split(), close_fds=True, stdout=self._lfile, stderr=STDOUT)
        except OSError as e:
            self._lfile.close()
            self._proc = None
            msg = 'Unable to run cmd {}: {}'.format(cmd, e)
            log.critical(msg)
            return pb.Response(success=False, comment=msg)

        sleep(1)
        if not self._proc or self._proc.poll():
            msg = 'Could not start tcpdump'
            log.info(msg)
            self._proc = None
            return pb.Response(success=False, comment=msg)

        msg = 'tcpdump started with process id {}'.format(self._proc.pid)
        log.info(msg)
        return pb.Response(success=True, comment=msg)

    def _stop_collection(self, force=True):
        log.info("stopping collection")
        if not self._proc:
            msg = 'No process running. Igorning stop.'
            log.warn(msg)
            return pb.Response(success=True, comment=msg)

        if self._proc:
            try:
                self._proc.terminate()
                sleep(1)
                self._proc.kill()
                self._proc.wait()
            except OSError as e:
                log.error('error stopping tcpdump process: {}'.format(e))

            self._lfile.close()
            self._proc = None

        return pb.Response(success=True, comment="")

    def _archive_dump(self, archivepath, dumpfile, tag):
        create = True
        if exists(archivepath):
            if not isdir(archivepath):
                return pb.Response(success=False, comment='Archive path exists and is not a directory.')

            create = False

        if create:
            try:
                makedirs(archivepath)
                log.info('Created archive dir: {}'.format(archivepath))
            except OSError as e:
                log.info('Directory already exists.')
        
        df = dumpfile if dumpfile else self.dumpfile
        if tag:
            destname = '{}.{}-{}-{}'.format(strftime('%Y%m%d-%H%M'), tag, self._node_name(), basename(df))
        else:
            destname = '{}.{}-{}'.format(strftime('%Y%m%d-%H%M'), self._node_name(), basename(df))

        copyfile(df, path_join(archivepath, destname))
        comment = 'Copied file: {} --> {}'.format(df, path_join(archivepath, destname))
        log.info(comment)
        return pb.Response(success=True, comment=comment)

    def _addr2iface(self, inaddr):
        for iface in interfaces():
            addrs = ifaddresses(iface)
            if AF_INET in addrs:
                for addr in addrs[AF_INET]:
                    if inaddr == addr['addr']:
                        return iface

        return None

    def _dest2iface(self, destination):
        addr = gethostbyname(destination)
        if not addr:
            log.critical('Unable to get address for {}'.format(destination))
            return None

        cmd = 'ip route get {}'.format(addr)
        try:
            out = check_output(cmd.split()).decode("utf-8")   # out ==> bytes to str
        except CalledProcessError as e:
            log.critical('Error invoking "{}": {}'.format(cmd, e))
            return None

        line = out.split('\n')[0].split()
        iface = line[line.index('dev')+1]  # dev name is always just after "dev" 

        if not iface:
            log.critical('Unable to find device name in ip route output: {}'.format(line))
            return None
        
        return iface

    def _node_name(self):
        return gethostname().split('.')[0]

