#vim fileencoding=utf8
from __future__ import division, print_function

import sys
import rays
from rays.compat import *
from .base import *

class TestStaticFileExtension(Base):
  def test_path(self):
    self.app.config("StaticFileExtension", {"url":"static/", "path": self.TEST_DIR})
    self.finish_app_config()

    url = self.url("static_file", "content.txt")
    assert "?" in url
    response = self.browser.get(url)
    assert b"test content" in response.body
    assert response.headers["Cache-Control"].startswith("max-age")
    assert "Expires" in response.headers
    assert response.status.startswith("200")

  def test_no_cache(self):
    self.app.config("StaticFileExtension", {
      "url":"static/", 
      "path": self.TEST_DIR,
      "cache": -1
    })
    self.finish_app_config()

    url = self.url("static_file", "content.txt")
    assert "?" not in url
    response = self.browser.get(url)
    assert response.headers["Cache-Control"] == "public"
    assert response.status.startswith("200")

  def test_if_modified_since_not_modified(self):
    self.app.config("StaticFileExtension", {
      "url":"static/", 
      "path": self.TEST_DIR,
    })
    self.finish_app_config()

    response = self.browser.get(self.url("static_file", "content.txt"),
                 headers = {"If-Modified-Since": "Thu, 01 Mar 2100 00:00:00 +0000"})
    assert response.status.startswith("304")

  def test_mb_content(self):
    self.app.config("StaticFileExtension", {"url":"static/", "path": self.TEST_DIR})
    self.finish_app_config()

    url = self.url("static_file", "mbcontent.txt")
    response = self.browser.get(url)
    assert u_("あいうえお") in response.body.decode("utf8") 
    assert response.status.startswith("200")

  #def test_mb_path(self):
  #  self.app.config("StaticFileExtension", {"url":"static/", "path": self.TEST_DIR})
  #  self.finish_app_config()

  #  url = self.url("static_file", u_("ファイル.txt"))
  #  response = self.browser.get(url)

  #  assert u_("コンテンツ") in response.body.decode("utf8") 
  #  assert response.status.startswith("200")
