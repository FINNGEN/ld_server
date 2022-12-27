#!/usr/bin/env python3

import sys, argparse
import gunicorn.app.base
from ld_server import app

def run_gunicorn(app, args):
    print("Running g🦄")
    class StandaloneGunicornApplication(gunicorn.app.base.BaseApplication):
        # from <http://docs.gunicorn.org/en/stable/custom.html>
        def __init__(self, app, opts=None):
            self.application = app
            self.options = opts or {}
            super().__init__()
        def load_config(self):
            for key, val in self.options.items():
                self.cfg.set(key, val)
        def load(self):
            return self.application
    options = {
        'bind': '{}:{}'.format(args.host, args.port),
        'reload': False,
        'workers': args.num_workers,
        'accesslog': args.accesslog,
        'access_log_format': '%(t)s | %(s)s | %(L)ss | %(m)s %(U)s | resp_len:%(B)s | referrer:"%(f)s" | ip:%(h)s | agent:%(a)s',
        'loglevel': args.loglevel,
        'timeout': 60,
        'worker_class': 'gevent',
        'preload_app': True,
        'max_requests': 100,
        'max_requests_jitter': 10
    }
    sga = StandaloneGunicornApplication(app, options)
    sga.run()

def run(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='the hostname to use to access this server')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--accesslog', default='-', help='the file to write the access log')
    parser.add_argument('--loglevel', default='info', help='log level')
    parser.add_argument('--num-workers', type=int, default=4, help='number of worker threads')
    args = parser.parse_args(argv)

    if args.host != '0.0.0.0':
        print('http://{}:{}'.format(args.host, args.port))

    run_gunicorn(app, args)

if __name__ == '__main__':
    run(sys.argv[1:])
