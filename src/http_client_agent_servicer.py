import logging
import pycurl
import threading
import time
import random

import http_client_agent_pb2 as pb
import http_client_agent_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

# Add instance of this agent to the server.
def AddServicer(server):
    pb_grpc.add_HttpClientAgentServicer_to_server(HttpClientAgentServicer(), server)

class HttpClientAgentServicer(pb_grpc.HttpClientAgentServicer):
    def __init__(self):
        log.debug('HttpClientAgentServicer created.')
        self.sizes = '1000'
        self.rate_limit = 0
        self.use_socks = False
        self.socks_server = None
        self.socks_port = None
        self.socks_version = None
        self.local_port = None

        self.servers = []

        # internal vars below here.
        self._db_configured = False
        self._prev_time = time.time()
        self._prev_bytes = 0
        self._progress_interval = 0
        self._url = "http://{}/gettext/{}"

        self._run_interval = 1   # how many seconds min between curl invocations.

        self._traffic_active = False
        self._thread = None
        
    def Configure(self, request, context):
        self.sizes = request.sizes if request.sizes else "1000"
        self.rate_limit = request.rate_limit if request.rate_limit else 0
        self.use_socks = request.use_socks if request.use_socks else False
        self.socks_server = request.socks_server if request.socks_server else None
        self.socks_port = request.socks_port if request.socks_port else None
        self.socks_version = request.socks_version if request.socks_version else None
        self.local_port = request.local_port if request.local_port else None
        return pb.Response(success=True, comment="agent configured.")

    def StartTraffic(self, request, context):
        self.servers = request.servers
        if self._traffic_active:
            return pb.Response(success=True, comment='Traffic already active.')
        
        if not self.servers:
            comment = 'Warning: no servers configured, so there is nothing to do.'
            log.info(comment)
            return pb.Responses(success=False, comment=comment)
        
        if self._thread:
            self._thread.join()
            self._thread = None

        self._traffic_active = True   # traffic thread will exit when it wakes up.
        self._thread = threading.Thread(target=self._run, args=())
        self._thread.daemon = True
        self._thread.start()

        return pb.Response(success=True, comment='Traffic started.')

    def StopTraffic(self, request, context):
        if not self._thread:
            return pb.Response(success=True, comment='Traffic not active. Igoring stop command.')

        self._traffic_active = False   # traffic thread will exit when it wakes up.
        return pb.Response(success=True, comment='Traffic stopped.')

    def ChangeTraffic(self, request, context):
        return pb.Response(success=False, comment="not implemented")

    def _run(self):
        '''Loop over curl calls to random servers until told to stop.'''
        log.info('curl client thread started.')
        while self._traffic_active:
            start_time = time.time()
            dst = self.servers[random.randint(0, len(self.servers) - 1)]
            c = pycurl.Curl()
            url = self._url.format(dst, int(eval(self.sizes)))
            log.info('requesting url: {}'.format(url))
            c.setopt(c.URL, url)
            c.setopt(c.NOPROGRESS, 0)
            c.setopt(c.PROGRESSFUNCTION, self._progress_callback)
            c.setopt(c.WRITEFUNCTION, lambda s: None) # Do nothing with received data.
            c.setopt(c.FOLLOWLOCATION, True)   # do we want this? Shouldn't come up in current setup.
            if self.local_port:
                c.setopt(c.LOCALPORT, self.local_port)

            if self.rate_limit:
                c.setopt(c.MAX_RECV_SPEED_LARGE, self.rate_limit)

            if self.use_socks:
                c.setopt(c.PROXY, '')
                c.setopt(c.PROXYPORT, self.socks_port)
                # version is only 4 or 5 as we check for this in confirmConfiguration()
                if self.socks_version == 4:
                    c.setopt(c.PROXYTYPE, c.PROXYTYPE_SOCKS4)
                else:
                    c.setopt(c.PROXYTYPE, c.PROXYTYPE_SOCKS5)

            self._prev_time = time.time() # seed the time for the callback function.
            self._prev_bytes = 0
            try:
                c.perform()
            except pycurl.error as e:
                log.error('Error running pycurl: {}'.format(e))
                c.close()
                raise e

            if c.getinfo(c.RESPONSE_CODE) != 200:
                log.error('Error with pycurl connection. Got response info/code: {} {}'.format(
                    c.getinfo(c.RESPONSE_CODE),
                    c.RESPONSE_CODE))

            self._save_post_metrics(dst, c)

            c.close()

            time.sleep(self._run_interval-(time.time()-start_time))

        log.info('curl client thread stopped.')

    def _progress_callback(self, dl_total, dl_sofar, ul_total, ul_sofar):
        # this function is invoked by pycurl many many times a second
        # during a connection. We may want to do as little computationally
        # expensive stuff here as possible. We may want to write results to
        # a queue, which is then evaluated once a second. 
        # now = time.time()    
        # self._progress_interval += now-self._prev_time
        # if self._progress_interval >= self.metric_period:
        #     dl_interval = dl_sofar-self._prev_bytes
        #     self._save_progress_metrics(self._progress_interval, dl_interval, dl_sofar,
        #                                 dl_total, ul_sofar, ul_total)
        #     self._progress_interval = 0.0
        #     self._prev_bytes = dl_sofar

        # self._prev_time = now
        return 0  # everything is OK.

    def _save_post_metrics(self, dst, c):  # c==pycurl instance
        pass

    def _save_progress_metrics(self, interval, dl_interval, dl_sofar, dl_total, ul_sofar, ul_total):
        # log.info('prog metrics: {}/{}/{}/{}/{}/{}'.format(
        #     interval, dl_interval, dl_sofar, dl_total, ul_sofar, ul_total))
        pass
