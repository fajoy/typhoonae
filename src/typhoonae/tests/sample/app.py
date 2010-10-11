import wsgiref.handlers

from google.appengine.ext import webapp


class MyRequestHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write("<html><body>Hello, World!</body></html>")


application = webapp.WSGIApplication([
  ('/', MyRequestHandler),
], debug=True)


def main():
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
