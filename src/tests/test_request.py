#vim fileencoding=utf8
from __future__ import division, print_function

import sys, codecs
import rays
from rays.compat import *
from .base import *

class TestRequest(Base):

  def test_get_header(self):
    app = self.app

    @app.get("")
    def index():
      assert app.req.get_header("Accept-Language") == "ja"
      assert app.req.get_header("HTTP_ACCEPT_LANGUAGE") == "ja"
      assert app.req.get_header("Content-type") == "text/plain"
      assert app.req.get_header("CONTENT_TYPE") == "text/plain"
      return "ok"

    self.finish_app_config()
    response = self.browser.get(self.url("index"),
     extra_environ = {"HTTP_ACCEPT_LANGUAGE": "ja",
                      "CONTENT_TYPE": "text/plain"})
    assert response.body == b"ok"

  def test_https(self):
    app = self.app

    @app.get("")
    def index():
      req = app.req
      assert req.is_ssl == True
      return app.req.action.name
    self.finish_app_config()
    response = self.browser.get(self.url("index"),
     extra_environ = {"HTTPS": "on"})

    response = self.browser.get(self.url("index"),
     extra_environ = {"HTTP_X_FORWARDED_PROTO": "https"})
    assert response.body == b"index"


  def test_input1(self):
    app = self.app

    @app.get("(int:\d+)/(unicode:.*)")
    def index(num_param, unicode_param):
      req = app.req
      assert num_param == 10
      assert unicode_param == u_("テスト")
      assert req.input.get("query") == u_("クエリ")
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("index", 10, u_("テスト"), 
      _query="query=%s"%urlquote(u_("クエリ").encode("utf8"))))
    assert response.body == b"index"

  def test_input_uploading_file(self):
    app = self.app

    @app.post("")
    def index():
      req = app.req
      assert req.input["file1"].filename == "mbcontent.txt"
      assert req.input["file1"].value.decode("utf8").strip() == u_("あいうえお")
      assert req.content_length != 0
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.post(self.url("index", 10, u_("テスト")), 
      upload_files=[("file1", 
                     "mbcontent.txt", 
                     codecs.open(os.path.join(self.TEST_DIR, "mbcontent.txt"), encoding="utf8").read().encode("utf8"))]
    )
    assert response.body == b"index"

  def test_input_post(self):
    app = self.app

    @app.post("")
    def index():
      req = app.req
      assert len(req.input["postdata"]) == 2
      assert req.input["postdata"][0] in (u_("ポストデータ1"), u_("ポストデータ2"))
      assert req.input["postdata"][1] in (u_("ポストデータ1"), u_("ポストデータ2"))

      assert req.input["obj"]["p1"] == u_("プロパティ1")
      assert req.input["obj"]["p2"] == u_("プロパティ2")
      assert isinstance(req.input["lst"], list)
      assert req.input["lst"][0] == u_("リスト1")
      assert req.input["lst"][1] == u_("リスト2")
      return app.req.action.name
    self.finish_app_config()

    req = app.req
    response = self.browser.post(self.url("index", 10, u_("テスト")), 
       [("postdata", b_("ポストデータ1")), ("postdata", b_("ポストデータ2")),
        ("obj[p1]", b_("プロパティ1")), ("obj[p2]", b_("プロパティ2")),
        ("lst[]", b_("リスト1")), ("lst[]", b_("リスト2"))
       ]
    )
    assert response.body == b"index"

  def test_cookie(self):
    app = self.app

    @app.get("set_cookie")
    def set_cookie():
      app.res.set_cookie("cookie_name", u_("クッキー値"))
      return app.req.action.name

    @app.get("assert_cookie")
    def assert_cookie():
      assert app.req.cookies["cookie_name"] == u_("クッキー値")
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("set_cookie"))
    assert response.body == b"set_cookie"
    response = self.browser.get(self.url("assert_cookie"))
    assert response.body == b"assert_cookie"

  def test_websocket(self):
    app = self.app

    @app.get("")
    def index():
      # TODO
      assert app.req.websocket == None
    self.finish_app_config()

    response = self.browser.get(self.url("index"))

  def test_is_xml_http_request(self):
    app = self.app

    @app.get("")
    def index():
      assert app.req.is_xml_http_request
      return "ok"
    self.finish_app_config()

    response = self.browser.get(self.url("index"), extra_environ= {
      "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"
    })
    assert response.body == b"ok"
    response = self.browser.get(self.url("index"), extra_environ= {
      "HTTP_X_REQUESTED_WITH": "XMLHTTPREQUEST"
    })
    assert response.body == b"ok"

  def test_http_version(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.http_version == 1.0
      return app.req.action.name
    @app.get("url_2")
    def url_2():
      assert app.req.http_version == 1.1
      return app.req.action.name
    @app.get("url_3")
    def url_3():
      assert app.req.http_version == 1.0
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"
    response = self.browser.get(self.url("url_2"), 
      extra_environ = {"SERVER_PROTOCOL": "HTTP/1.1"})
    assert response.body == b"url_2"
    response = self.browser.get(self.url("url_3"), 
      extra_environ = {"SERVER_PROTOCOL": "HTTP/INVALID"})
    assert response.body == b"url_3"

  def test_method(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.method == "get"
      return app.req.action.name
    @app.post("url_2")
    def url_2():
      assert app.req.method == "post"
      return app.req.action.name
    @app.delete("url_3")
    def url_3():
      assert app.req.method == "delete"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"
    response = self.browser.post(self.url("url_2"))
    assert response.body == b"url_2"
    response = self.browser.post(self.url("url_3"), {"_method": "delete"})
    assert response.body == b"url_3"

  def test_ua(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.ua == "webtest"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_USER_AGENT": "webtest"})
    assert response.body == b"url_1"

  def test_format(self):
    app = self.app

    @app.get("url_1.html")
    def url_1():
      assert app.req.format == "text/html"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"

  def test_host_with_port(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.host_with_port == "localhost:80"
      return app.req.action.name
    @app.get("url_2")
    def url_2():
      assert app.req.host_with_port == "proxy_host:8080"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"
    response = self.browser.get(self.url("url_2"),
      extra_environ={"HTTP_X_FORWARDED_HOST": "localhost:80, proxy_host:8080"})
    assert response.body == b"url_2"

  def test_host(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.host == "localhost"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"

  def test_port(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.port == 80
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"))
    assert response.body == b"url_1"

  def test_referer(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.referer == "http://localhost/referer"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_REFERER": "http://localhost/referer"})
    assert response.body == b"url_1"

  def test_remote_addr(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      assert app.req.remote_addr == "127.0.0.1"
      return app.req.action.name
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"REMOTE_ADDR": "127.0.0.1"})
    assert response.body == b"url_1"

  def test_accept(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      values = app.req.accept.values
      assert len(values) == 5
      assert repr(values[0]) == "<AcceptanceValue text/html;level=1>"
      assert repr(values[1]) == "<AcceptanceValue text/html;q=0.7>"
      assert repr(values[2]).startswith("<AcceptanceValue text/html;")
      assert repr(values[3]) == "<AcceptanceValue text/*;q=0.3>"
      assert repr(values[4]) == "<AcceptanceValue */*;q=0.2>"

      assert app.req.accept.accepts("text").q == 1.0
      assert app.req.accept.accepts("text", "html").q == 1.0
      assert app.req.accept.accepts("*").q == 1.0
      assert app.req.accept.accepts("jpeg").q == 0.2
      assert app.req.accept.accepts("text", "xml").q == 0.3
      assert app.req.accept.accepts("text", "html", {"level":"2"}).q == 0.4

      return "ok1"

    @app.get("url_2")
    def url_2():
      values = app.req.accept.values
      assert len(values) == 5
      assert repr(values[0]) == "<AcceptanceValue text/html;q=0.3>"
      return "ok2"


    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_ACCEPT": "text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.2"})
    assert b"ok1" in response.body

    response = self.browser.get(self.url("url_2"), 
      extra_environ={"HTTP_ACCEPT": "text/*;q=0.3, text/*;q=0.3, text/*;q=0.3;level=1,text/html;q=0.3, */*;q=0.3"})
    assert b"ok2" in response.body


  def test_accept_charset(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      values = app.req.accept_charset.values
      assert len(values) == 2
      assert repr(values[0]) == "<AcceptanceValue iso-8859-5>"
      assert repr(values[1]) == "<AcceptanceValue unicode-1-1;q=0.8>"
      return "ok1"

    @app.get("url_2")
    def url_2():
      values = app.req.accept_charset.values
      assert len(values) == 1
      assert repr(values[0]) == "<AcceptanceValue iso-8859-1;q=1>"
      return "ok2"
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_ACCEPT_CHARSET": "iso-8859-5, unicode-1-1;q=0.8"})
    assert b"ok1" in response.body

    response = self.browser.get(self.url("url_2"), 
      extra_environ={"HTTP_ACCEPT_CHARSET": ""})
    assert b"ok2" in response.body


  def test_accept_language(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      values = app.req.accept_language.values
      assert len(values) == 3
      assert repr(values[0]) == "<AcceptanceValue da>"
      assert repr(values[1]) == "<AcceptanceValue en/gb;q=0.8>"
      assert repr(values[2]).startswith("<AcceptanceValue en;q=0.7")


      assert app.req.accept_language.accepts("da").q == 1.0
      assert app.req.accept_language.accepts("en", "gb").q == 0.8
      assert app.req.accept_language.accepts("en", "us").q == 0.7
      assert app.req.accept_language.accepts("ja") is None
      return "ok"


    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_ACCEPT_LANGUAGE": "da, en-gb;q=0.8, en;q=0.7"})
    assert b"ok" in response.body


  def test_accept_encoding(self):
    app = self.app

    @app.get("url_1")
    def url_1():
      values = app.req.accept_encoding.values
      assert len(values) == 3
      assert repr(values[0]) == "<AcceptanceValue gzip;q=1.0>"
      assert repr(values[1]) == "<AcceptanceValue identity;q=0.5>"
      assert not app.req.accept_encoding.accepts("compress")
      return "ok1"

    @app.get("url_2")
    def url_2():
      values = app.req.accept_encoding.values
      assert len(values) == 1
      assert repr(values[0]) == "<AcceptanceValue identity;q=1>"
      return "ok2"
    self.finish_app_config()

    response = self.browser.get(self.url("url_1"), 
      extra_environ={"HTTP_ACCEPT_ENCODING": "gzip;q=1.0, identity; q=0.5, *;q=0"})
    assert b"ok1" in response.body

    response = self.browser.get(self.url("url_2"), 
      extra_environ={"HTTP_ACCEPT_ENCODING": ""})
    assert b"ok2" in response.body
