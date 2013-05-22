#vim fileencoding=utf8
from __future__ import division, print_function

import os.path, shutil
import re
import time
import logging

import rays
from rays.compat import *

import pytest
import requests.cookies
from webtest import TestApp

class RaysTestApp(TestApp):
  def set_cookie(self, name, value, **kwargs):
    cookie = requests.cookies.create_cookie(name, value, **kwargs)
    self.cookiejar.set_cookie(cookie)

class Base(object):
  TEST_DIR = os.path.dirname(os.path.abspath(__file__))
  sys.path.append(TEST_DIR)

  @classmethod
  def setup_class(cls, *args):
    pass

  @classmethod
  def teardown_class(cls, *args):
    pass

  def try_removing_file(self, file, retry_limit = 10):
    if not os.path.isfile(file):
      return

    for i in range(retry_limit):
      try:
        os.remove(file)
        return
      except Exception as e:
        time.sleep(0.1)
    reraise(e.__class__, e, sys.exc_info()[-1])

  def finish_app_config(self):
    self.browser.get("/_dummy")

  def url(self, name, *args, **kw):
    return re.sub("http[s]?://localhost", "", getattr(self.app.url, name)(*args, **kw))

  def init_browser(self, environ = None):
    env = {"wsgi.url_scheme": "http", 
           "HTTP_HOST" : "localhost",
           "SERVER_PORT": "80"}
    env.update(environ or {})
    self.browser = RaysTestApp(self.app, env)

  def init_app(self, environ = None):
    self.app = rays.Application(debug=True)
    self.app.logger.setLevel(logging.INFO)
    self.app.initialize()
    @self.app.get("_dummy")
    def _dummy():
      return ""
    self.init_browser(environ)

  def setup_method(self, method):
    self.init_app()

  def teardown_method(self, method):
    pass

class SkipIf(object):
  try:
    import gevent
    _no_gevent = False
  except:
    _no_gevent = True
  no_gevent = pytest.mark.skipif("SkipIf._no_gevent")
