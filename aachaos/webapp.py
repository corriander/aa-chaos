import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO: tsk tsk, hardcoding.
        path = '/tmp/aachaos_usage_monitor.svg'
        self.render(path)

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(9988)
    tornado.ioloop.IOLoop.current().start()
