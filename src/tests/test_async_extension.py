#vim fileencoding=utf8
from __future__ import division, print_function

import sys, time
import rays
from rays.compat import *
from .base import *

try:
  import gevent
except ImportError:
  pass

class TestAsyncExtention(Base):
  @SkipIf.no_gevent
  def test_async_response(self):
    app = self.app
    app.config("AsyncExtension", { })
    def worker():
      app.ext.async.write(u_("1"))
      gevent.sleep(1)
      app.ext.async.write(u_("2"))
      gevent.sleep(2)
      app.ext.async.write(u_("3"))
      app.ext.async.finish()

    @app.get("async")
    @app.ext.async
    def async():
      gevent.spawn(app.ext.async.callback(worker))

    @app.ext.async.on_connection_close
    def on_connection_close(close_by_client):
      if close_by_client:
        app.logger.info("Connection closed: %s"%app.req.remote_addr)

    self.finish_app_config()
    started_at = time.time()
    assert "123" in self.browser.get(self.url("async")).body
    assert (time.time() - started_at) > 3

  @SkipIf.no_gevent
  def test_async_empty_response(self):
    app = self.app
    app.config("AsyncExtension", { })
    def worker():
      app.ext.async.finish()

    @app.get("async")
    @app.ext.async
    def async():
      gevent.spawn(app.ext.async.callback(worker))

    self.finish_app_config()
    started_at = time.time()
    response = self.browser.get(self.url("async"))
    assert response.body.strip() == b""
    assert response.status.startswith("200")

  @SkipIf.no_gevent
  def test_async_error_response(self):
    app = self.app
    app.config("AsyncExtension", { })
    def error_worker():
      gevent.sleep(1)
      raise Exception("TEST_ASYNC_ERROR_RESPONSE")

    @app.get("error")
    @app.ext.async
    def error():
      gevent.spawn(app.ext.async.callback(error_worker))

    self.finish_app_config()
    response = self.browser.get(self.url("error"), expect_errors=True)
    assert response.status.startswith("500")
    assert "TEST_ASYNC_ERROR_RESPONSE" in response.body
