import tornado.ioloop
import tornado.web


# TODO: fix hardcoding / filename
FIG_PATH = '/tmp/aachaos_usage_monitor.svg'
TMP_PATH = '/tmp/aachaos_usage_monitor.tmp.svg'


class QuasiStaticHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control',
                        'no-store, no-cache, must-revalidate')


def make_app():
    return tornado.web.Application([
        # The fig could be mapped to e.g. server:port/netquota with
        # r'/netquota()'
        (r'/()', QuasiStaticHandler, {'path': FIG_PATH}),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(8889)
    tornado.ioloop.IOLoop.current().start()
