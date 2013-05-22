#!/usr/bin/env python
from __future__ import division, print_function
from gevent import monkey; monkey.patch_all()
from rays import *
import os.path, traceback, locale

app = Application()
APP_DIR = os.path.dirname(__file__)
SOCKETS = set([])

app.config([
  ("debug", True),
  ("renderer", {"template_dir":os.path.join(APP_DIR, "templates"),
                "cache_dir":os.path.join(APP_DIR, "templates/caches")}),
  ("StaticFileExtension", {"url":"statics/", "path": os.path.join(APP_DIR, "statics")})
])

@app.get("chat")
def chat():
  try:
    ws = app.req.websocket
    SOCKETS.add(ws)
    app.logger.info("accepts: %s"%repr(ws.socket))

    while True:
      msg = ws.receive()
      if msg is None:
        break
      app.logger.info(u_("receive: '%s' from %s")%(str(msg), repr(ws.socket)))

      error_sockets = set([])
      for s in SOCKETS:
        try:
          s.send(msg)
        except Exception, e:
          app.logger.warning(e)
          error_sockets.add(s)

      for s in error_sockets:
        SOCKETS.remove(s)
  except Exception, e:
    app.logger.error(e)

@app.get("")
def index():
  return app.renderer.index()

if __name__ == "__main__":
  app.run_gevent(port=7000, host="0.0.0.0", websocket=True)
