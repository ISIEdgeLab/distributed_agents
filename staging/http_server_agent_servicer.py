import logging
import shutil
import os
import stat
import platform
from subprocess import check_output, CalledProcessError, call

import sys
sys.path.append('./pb')
import http_server_agent_pb2 as pb
import http_server_agent_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

# Add instance of this agent to the server.
def AddServicer(server):
    pb_grpc.add_HttpServerAgentServicer_to_server(HttpServerAgentServicer(), server)

class HttpServerAgentServicer(pb_grpc.HttpServerAgentServicer):
    def __init__(self):
        log.debug('HttpServerAgentServicer created.')

        # supported platforms are constrained.
        # may work on others, but would not want
        # to rely on that.
        dist = platform.dist()
        if dist[0] != 'Ubuntu':
            raise ApacheAgentException('Unsupported OS: {}'.format(dist))

        maj = int(dist[1].split('.')[0])
        if not 12 <= maj <= 16:
            raise ApacheAgentException('Unsupported Ubuntu Version: {}'.format(maj))

    def StartServer(self, request, context):
        self._configure()
        self.StopServer(None, None)

        cmd = 'sudo service apache2 restart'
        log.info('Running cmd: {}'.format(cmd))
        try:
            check_output(cmd.split(), close_fds=True)
        except CalledProcessError as e:
            comment = 'Error invoking "{}": {}'.format(cmd, e)
            log.critical(comment)
            return pb.Response(success=False, comment=comment)

        comment = 'Apache started.'
        log.info(comment)
        return pb.Response(success=True, comment=comment)

    def StopServer(self, request, context):
        cmd = 'sudo service apache2 stop'
        try:
            check_output(cmd.split(), close_fds=True)
        except CalledProcessError as e:
            comment = 'Error invoking "{}": {}'.format(cmd, e)
            log.critical(comment)
            return pb.Response(success=False, comment=comment)

        comment = 'Apache stopped.'
        log.info(comment)
        return pb.Response(success=True, comment=comment)

    def _configure(self):
        # create and enable our site.
        cwd = os.path.dirname(__file__)
        # Apache 2.2 wants no ".conf" while 2.4+ does. So give both.
        shutil.copyfile(os.path.join(cwd, 'traffic_gen'),
                        '/etc/apache2/sites-available/traffic_gen')
        shutil.copyfile(os.path.join(cwd, 'traffic_gen'),
                        '/etc/apache2/sites-available/traffic_gen.conf')

        # Have apache use our site and remove the default one.
        try:
            check_output('a2ensite traffic_gen'.split(), close_fds=True)
            call('a2dissite default'.split(), close_fds=True)
            call('a2dissite 000-default'.split(), close_fds=True)
        except CalledProcessError as e:
            comment = 'Error updating Apache to use our flask applications.'
            log.critical(comment)
            return pb.Response(success=False, comment=comment)

        # create the WSGI site itself.
        sitedir = '/var/www/traffic_gen'
        try:
            os.stat(sitedir)
        except OSError:
            os.mkdir(sitedir)

        for f in ['traffic_gen.py', 'traffic_gen.wsgi']:
            shutil.copyfile(os.path.join(cwd, f), os.path.join(sitedir, f))
        
        # the script must be executable by apache
        perms = stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP
        os.chmod(os.path.join(sitedir, 'traffic_gen.py'), perms)

        # bad way to do this, but python does not seem to have a straightforward way
        check_output('chown -R www-data {}'.format(sitedir).split(), close_fds=True)
