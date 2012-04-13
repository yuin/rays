#vim fileencoding=utf8
from __future__ import division, print_function

import sys, codecs, os.path
from rays import *
from rays.compat import *
from .base import *

import pytest

def start_response(status, headers):
  assert True

class TestResponse(Base):
  def test_accept_ranges(self):
    res = Response(start_response)
    assert res.get_header("Accept-Ranges") == "none"

  def test_content_type_getter_and_setter(self):
    res = Response(start_response)
    res.content_type = "text/xml; charset=UTF8"

    assert res.get_header("Content-type") == "text/xml; charset=UTF8"
    assert res.content_type == "text/xml; charset=UTF8"

  def test_status_getter(self):
    res = Response(start_response)
    res.status_code = 301
    assert res.status == "301 Moved Permanently"

  def test_start_response(self):
    def error_start_response(status, headers):
      assert False

    res = Response(start_response)
    res.start_response()

    res._start_response = error_start_response
    res.start_response()

  def test_set_and_get_header(self):
    res = Response(start_response)
    res.set_header("X-test", "value")
    assert res.get_header("X-test") == "value"

    res.del_header("X-test")
    assert res.get_header("X-test") == None

    res.set_header("X-multiple-header1", "value1", unique=False)
    res.set_header("X-multiple-header1", "value2", unique=False)
    assert res.get_header("X-multiple-header1") == ["value1", "value2"]

    res.set_header("X-multiple-header2", "value1", unique=True)
    res.set_header("X-multiple-header2", "value2", unique=True)
    assert res.get_header("X-multiple-header2") == "value2"


  def test_set_cookie(self):
    res = Response(start_response)
    res.set_cookie("test_cookie", u_("クッキー値"), 
                   expires = 60*60,
                   domain  = "example.com",
                   secure  = True,
                   comment = "test cookie")
    res.set_cookie("cookie1", "value")
    res.set_cookie("cookie2", "value", expires = -1)

    cookie_header = res.get_header("Set-Cookie")[0]
    assert "test_cookie=%E3%82%AF%E3%83%83%E3%82%AD%E3%83%BC%E5%80%A4;" in cookie_header
    assert "Comment=test cookie;" in cookie_header
    assert "Domain=example.com;"  in cookie_header
    assert "expires=" in cookie_header 
    assert "Path=/;" in cookie_header
    assert "secure" in cookie_header

  def test_abort(self):
    res = Response(start_response)
    try:
      res.badrequest("Invalid operation")
      assert False
    except Abort as e:
      assert res.status_code == 400
      assert e.thunk == "Invalid operation"
      assert e.status == "400 Bad Request"
      
  def test_redirect(self):
    res = Response(start_response)
    try:
      res.redirect("http://example.com/")
      assert False
    except ReturnResponse as e:
      assert res.status_code == 303
      assert res.get_header("Location") == "http://example.com/"

  def test_not_modified(self):
    res = Response(start_response)
    res.set_header("X-custom-header", "value")

    try:
      res.not_modified()
      assert False
    except ReturnResponse as e:
      assert res.status_code == 304
      assert e.thunk == []
      assert res.get_header("X-custom-header") != None
      assert res.get_header("Content-type") == None

  def test_send_file_not_found(self):
    res = Response(start_response)
    with pytest.raises(Abort):
      res.send_file("file_does_not_exist")
    res.status_code = 404

  def test_send_file_mimetype(self):
    res = Response(start_response)
    with pytest.raises(ReturnResponse):
      res.send_file(os.path.join(self.TEST_DIR, "base.py"))
    assert res.content_type == "text/x-python"

    res = Response(start_response)
    res.content_type = ""
    with pytest.raises(ReturnResponse):
      res.send_file(os.path.join(self.TEST_DIR, "file.unknown_ext"),
        mimetype="text/unknown")
    assert res.content_type == "text/unknown"

  def test_send_file(self):
    res = Response(start_response)
    with pytest.raises(ReturnResponse):
      res.send_file(os.path.join(self.TEST_DIR, "content.txt"))
    assert res.get_header("Content-Length") == '15'
    # TODO validate by the current time
    assert res.get_header("Last-Modified")
    assert res.get_header("Etag")



  def test_is_success(self):
    res = Response(start_response)

    res.status_code = 199
    assert (not res.is_success)
    res.status_code = 200
    assert res.is_success
    res.status_code = 201
    assert res.is_success
    res.status_code = 399
    assert res.is_success
    res.status_code = 400
    assert (not res.is_success)
    res.status_code = 401
    assert (not res.is_success)

  def test_is_abort(self):
    res = Response(start_response)
    res.exception = Abort("", 404)
    assert res.is_abort

  def test_is_error(self):
    res = Response(start_response)
    res.status_code = 500

    assert res.is_error

    res.exception = Abort("", 500)

    assert (not res.is_error)


