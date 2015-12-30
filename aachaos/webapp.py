import os

import tornado.ioloop
import tornado.web

from aachaos.config import settings


FIG_PATH = settings.get('Path', 'Figure')
TMP_PATH = '.'.join([FIG_PATH, 'tmp'])


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


def create_figure():
    plotter = vis.Plotter()
    plotter.plot_month()


if __name__ == "__main__":
    # Ensure the figure is actually present (e.g. on startup).
    if not os.path.isfile(FIG_PATH):
        create_figure()

    app = make_app()
    app.listen(8889)
    tornado.ioloop.IOLoop.current().start()
