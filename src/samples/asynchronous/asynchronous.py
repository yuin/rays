#vim: fileencoding=utf8
from __future__ import division, print_function
from gevent import monkey; monkey.patch_all()
import gevent
import gevent.pool

from rays import *
from rays.compat import *
import time

app = Application()
APP_DIR = os.path.dirname(__file__)

app.config([
  ("debug", True),
  ("AsyncExtension", {})
])

def worker():
  app.ext.async.write(u_("1"))
  time.sleep(5)
  app.ext.async.write(u_("2"))
  time.sleep(2)
  app.ext.async.write(u_("3"))
  app.ext.async.finish()

def error_worker():
  time.sleep(5)
  raise Exception("error")

@app.get("")
def index():
  return "<a href='async'> async </a><br /><a href='error'> error </a>"

@app.get("async")
@app.ext.async
def async():
  gevent.spawn(app.ext.async.callback(worker))

@app.get("error")
@app.ext.async
def error():
  gevent.spawn(app.ext.async.callback(error_worker))

@app.ext.async.on_connection_close
def on_connection_close(close_by_client):
  if close_by_client:
    app.logger.info("Connection closed: %s"%app.req.remote_addr)

if __name__ == "__main__":
  pool = gevent.pool.Pool(1000)
  app.run_gevent(port=7000, host="0.0.0.0", spawn = pool)
