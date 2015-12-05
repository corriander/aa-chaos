import tornado.ioloop
import tornado.web

from aachaos.get import History

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        path = '/tmp/usage.svg'
        # This should be spat out every time a new datapoint is
        # collected, not on request.
        History().plot_this_month(path)
        self.render(path)

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(9988)
    tornado.ioloop.IOLoop.current().start()
