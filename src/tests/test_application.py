#vim fileencoding=utf8
from __future__ import division, print_function

import sys
import itertools
from rays import *
from rays.compat import *
from .base import *

import pytest

class TestApplication(Base):
  def test_define_tls_property(self):
    self.finish_app_config()
    self.app.define_tls_property("prop", "test property")

    assert self.app.prop == None
    assert "prop" in self.app.tls_names

  def test_copy_tls_property(self):
    self.finish_app_config()
    self.app.define_tls_property("prop", "test property")
    tls = self.app.copy_tls_property()
    assert len(tls) == 3
    assert all(v in ["res", "req", "prop"] for v in tls)

    tls["prop"] = "value"
    self.app.copy_tls_property(tls)
    assert len(tls) == 3
    assert all(v in ["res", "req", "prop"] for v in tls)
    assert self.app.prop == "value"

  def test_get_renderer(self):
    self.finish_app_config()
    assert isinstance(self.app.renderer, Renderer)

  def test_set_renderer(self):
    self.app.renderer = None
    assert self.app._renderer == None

  def test_config(self):
    self.app.config([
      ("base", "/"),
      ("charset", "utf8"),
      ("debug", True),
      ("logger",True),
      ("renderer", {"template_dir": "./t"}),
      ("app_ver", 1.0)
    ])
    self.finish_app_config()

    assert self.app.base == "/"
    assert self.app.charset == "utf8"
    assert self.app.debug == True
    assert self.app.logger == True
    assert self.app.renderer.template_dir == "./t"
    assert self.app.vars.app_ver == 1.0

  def test_helper(self):
    @self.app.helper
    def helper_func(helper):
      return "value"
    self.finish_app_config()

    assert self.app.renderer.template_globals["h"].helper_func() == "value"
    

  def test_init_routes(self):
    @self.app.get("")
    def index():
      pass
    self.finish_app_config()
    
    assert len(self.app.url_cache) == 0
    assert "index" in self.app.actions_map

  def test_get(self):
    @self.app.get("")
    def index():
      return "ok"
    self.finish_app_config()
    assert b"ok" in self.browser.get(self.url("index")).body
    assert self.browser.post(self.url("index"), expect_errors = True).status.startswith("405")

  def test_post(self):
    @self.app.post("")
    def index():
      return "ok"
    self.finish_app_config()
    assert b"ok" in self.browser.post(self.url("index")).body
    assert self.browser.get(self.url("index"), expect_errors = True).status.startswith("405")

  def test_put(self):
    @self.app.put("")
    def index():
      return "ok"
    self.finish_app_config()
    assert b"ok" in self.browser.put(self.url("index")).body
    assert self.browser.get(self.url("index"), expect_errors = True).status.startswith("405")

  def test_delete(self):
    @self.app.delete("")
    def index():
      return "ok"
    self.finish_app_config()
    assert b"ok" in self.browser.delete(self.url("index")).body
    assert self.browser.get(self.url("index"), expect_errors = True).status.startswith("405")

  def test_head(self):
    @self.app.head("")
    def index():
      return "ok"
    self.finish_app_config()
    assert self.browser.head(self.url("index")).body.strip() == b""
    assert self.browser.get(self.url("index"), expect_errors = True).status.startswith("405")

  def test_apply_filer(self):
    def filter(*a, **k):
      pass
      
    @self.app.apply_filter(filter)
    @self.app.get("")
    def index():
      return "ok"
    self.finish_app_config()

    assert len(self.app.actions_map["index"].filters) == 1

  def test_filter(self):
    check_dict = {}
    app = self.app

    def filter_a(*args):
      check_dict["filter_a_pre"] = True
      yield
      app.res.content = "aaa"
      check_dict["filter_a_after"] = True
  
    def filter_b(*args):
      check_dict["filter_b_pre"] = True
      yield
      app.res.content = "bbb"
      check_dict["filter_b_after"] = True
  
    def filter_c(*args):
      check_dict["filter_c_pre"] = True
      yield
      app.res.content = "ccc"
      check_dict["filter_c_after"] = True
  
    with app.filter(filter_a, [filter_b, {"except":["test_get1"]}]):
      @app.get("test")
      def test_get():
        assert check_dict["filter_a_pre"]
        assert "filter_a_after" not in check_dict
        return ""
  
      @app.get("test_error")
      def test_get_error():
        app.res.notfound()
  
      with app.filter(filter_c):
        @app.get("test1")
        def test_get1():
          return ""
  
      @app.get("_test_without")
      def _test_without():
        return ""
  
    @app.get("test_without")
    def test_without():
      return _test_without()

    self.finish_app_config()
  
    check_dict = {}
    assert b"aaa" == self.browser.get(self.url("test_get")).body.strip()
    assert check_dict["filter_a_pre"]
    assert check_dict["filter_a_after"]
    assert check_dict["filter_b_pre"]
    assert check_dict["filter_b_after"]
    assert "filter_c_pre" not in check_dict
    assert "filter_c_after" not in check_dict
  
    check_dict = {}
    with pytest.raises(Exception):
      self.browser.get(self.url("test_get_error"))
    assert check_dict["filter_a_pre"]
    assert "filter_a_after" not in check_dict
    assert check_dict["filter_b_pre"]
    assert "filter_b_after" not in check_dict
    assert "filter_c_pre" not in check_dict
    assert "filter_c_after" not in check_dict
  
    check_dict = {}
    assert b"aaa" == self.browser.get(self.url("test_get1")).body.strip()
    assert check_dict["filter_a_pre"]
    assert check_dict["filter_a_after"]
    assert "filter_b_pre" not in check_dict
    assert "filter_b_after" not in check_dict
    assert check_dict["filter_c_pre"]
    assert check_dict["filter_c_after"]
  
    check_dict = {}
    assert b"" == self.browser.get(self.url("test_without")).body.strip()
    assert "filter_a_pre" not in check_dict
    assert "filter_a_after" not in check_dict
    assert "filter_b_pre" not in check_dict
    assert "filter_b_after" not in check_dict

  def test_filter_order(self):
    app = self.app

    buffer = []
    def filter_a(*a, **k):
      buffer.append(1)
      yield
      buffer.append(6)

    def filter_b(*a, **k):
      buffer.append(2)
      yield
      buffer.append(5)

    def filter_c(*a, **k):
      buffer.append(3)
      yield
      buffer.append(4)

    with app.filter(filter_a, filter_b):
      with app.filter(filter_c):
        @app.get("test")
        def test_get():
          return "ok"

    self.finish_app_config()

    assert b"ok" in self.browser.get(self.url("test_get")).body
    assert [1,2,3,4,5,6] == buffer

  def test_before_hooks1(self):
    app = self.app

    check_dict = {}
    @app.get("test")
    def test_get():
      return ""
  
    @app.get("test1")
    def test_get1():
      # raise a error
      return foo
  
    @app.get("test2")
    def test_get2():
      # abort
      app.res.notfound()
    self.finish_app_config()
  
    check_dict = {}
    @app.hook("before_call")
    def hook1(env, start_response):
      check_dict[0] = True
    @app.hook("before_call")
    def hook2(env, start_response):
      check_dict[1] = True
      raise Exception()
    @app.hook("before_call")
    def hook3(env, start_response):
      check_dict[2] = True
  
    with pytest.raises(Exception):
      self.browser.get(self.url("test_get"))
    assert check_dict[0]
    assert check_dict[1]
    assert 2 not in check_dict
  
  
  def test_before_hooks2(self):
    app = self.app
    check_dict = {}
    @app.get("test")
    def test_get():
      return ""
  
    @app.get("test1")
    def test_get1():
      # raise a error
      return foo
  
    @app.get("test2")
    def test_get2():
      # abort
      app.res.notfound()
    @app.hook("before_action")
    def hook():
      assert hasattr(app.req, "params")
      assert hasattr(app.req, "action")
      assert "" == app.res.content
      check_dict[0] = True
      return ""
    self.finish_app_config()

    self.browser.get(self.url("test_get"))
    assert check_dict[0]
  
  def test_after_hooks(self):
    app = self.app
    check_dict = DefaultAttrDict()
    @app.get("test_success")
    def test_get():
      check_dict.sucess = True
      return ""
  
    @app.get("test_error")
    def test_get1():
      check_dict.error = True
      return foo
  
    @app.get("test_abort")
    def test_get2():
      check_dict.abort = True
      app.res.notfound()
  
    @app.hook("before_start_response")
    def hook():
      if app.res.is_success:
        check_dict.hook_success = True
      elif app.res.is_abort:
        check_dict.hook_abort = True
      elif app.res.is_error:
        check_dict.hook_error = True
    self.finish_app_config()
  
    check_dict.clear()
    self.browser.get(self.url("test_get"))
    assert check_dict.sucess
    assert check_dict.hook_success

    check_dict.clear()
    try:
      self.browser.get(self.url("test_get1"))
      assert False
    except:
      assert check_dict.error
      assert check_dict.hook_error
  
    check_dict.clear()
    try:
      self.browser.get(self.url("test_get2"))
      assert False
    except:
      assert check_dict.abort
      assert check_dict.hook_abort
      
      
  def test_not_found(self):
    app = self.app
    @app.error(404)
    def _404():
      return "--notfound--"
    self.finish_app_config()
  
    response = self.browser.get("/unknwon_path", expect_errors=True)
    assert response.status.startswith("404")
    assert b"--notfound--" == response.body.strip()
  
  def test_redirect(self):
    app = self.app
    @app.get("get")
    def get():
      return "ok"
  
    @app.get("redirect")
    def redirect():
      app.res.redirect(app.url.get())
    self.finish_app_config()
  
    response = self.browser.get(self.url("redirect"))
    response = response.follow()
    assert b"ok" in response.body

  def test_url_builder(self):
    app = self.app
    @app.get("get/(int:\d+)/(unicode:[^/]+)/(int:\d+)")
    def get():
      return "ok"
    self.finish_app_config()

    assert "http://localhost/get/10/%E3%83%91%E3%82%B9/9" == app.url.get(10, u_("パス"), 9)
    assert "http://localhost/get/10/str/9?query" == app.url.get(10, "str", 9, _query="query")
    assert "https://localhost/get/10/str/9?query" == app.url.get(10, "str", 9, _query="query", _ssl=True)

    self.init_app({"wsgi.url_scheme": "https"})
    app = self.app
    @app.get("get/(int:\d+)/(unicode:[^/]+)/(int:\d+)")
    def get():
      return "ok"
    self.finish_app_config()

    assert "https://localhost/get/10/str/9" == app.url.get(10, "str", 9)
    assert "http://localhost/get/10/str/9?query" == app.url.get(10, "str", 9, _query="query", _ssl=False)

  def test_handle_exception_with_debugging(self):
    app = self.app
    @app.get("get1")
    def get1():
      app.res.status_code = 500
      raise Abort("ERROR", 500)
    @app.get("get2")
    def get2():
      app.res.status_code = 500
      raise Abort(lambda : "ERROR", 500)
    @app.get("get3")
    def get3():
      app.res.status_code = 500
      raise Abort(lambda : return_response(lambda : "ERROR"), 500)
    @app.get("get4")
    def get4():
      assert False
    @app.get("get5")
    def get5():
      foo
    self.finish_app_config()

    for i in irange(1,4):
      response = self.browser.get(self.url("get%d"%i), expect_errors=True)
      assert response.status.startswith("500")
      assert b"ERROR" in response.body
    with pytest.raises(AssertionError):
      self.browser.get(self.url("get4"))

    response = self.browser.get(self.url("get5"), expect_errors=True)
    assert response.status.startswith("500")
    assert b"NameError: global name" in response.body

  def test_handle_exception_with_no_debugging_and_error_handlers(self):
    app = self.app
    app.debug = False

    @app.get("get1")
    def get1():
      foo

    @app.error(500)
    def error_500():
      return "MY ERROR MESSAGE"


    self.finish_app_config()
    response = self.browser.get(self.url("get1"), expect_errors=True)
    assert response.status.startswith("500")
    assert b"MY ERROR MESSAGE" in response.body

  def test_handle_exception_with_no_debugging_and_no_error_handlers(self):
    app = self.app
    app.debug = False

    @app.get("get1")
    def get1():
      foo

    self.finish_app_config()
    response = self.browser.get(self.url("get1"), expect_errors=True)
    assert response.status.startswith("500")
    assert b"500 Internal Server Error" in response.body

  def test_convert_content(self):
    app = self.app
    @app.get("get1")
    def get1():
      return BytesIO(b"")
    @app.get("get2")
    def get2():
      return b"bytes"
    @app.get("get3")
    def get3():
      return u_("ユニコード")
    def wrapper(v):
      return [b"wrapped"]
    self.finish_app_config()

    response = self.browser.get(self.url("get1"), extra_environ={"wsgi.file_wrapper":wrapper})
    assert b"wrapped" in response.body 

    response = self.browser.get(self.url("get2"))
    assert b"bytes" in response.body

    response = self.browser.get(self.url("get3"))
    assert u_("ユニコード").encode("utf8") in response.body

  def test_javascript_url_builder(self):
    app = self.app
    @app.get("get1/(int:\d+)")
    def get1(id):
      pass
    @app.get("get2/(int:\d+)/(unicode:\s+)")
    def get2(id, name):
      pass
    self.finish_app_config()

    patterns = itertools.permutations(['"get1": ["/get1/", ""]', '"get2": ["/get2/", "/", ""]', '"_dummy": ["/_dummy"]'])
    assert any(["""if(typeof(rays) == 'undefined'){ window.rays={};}(function(){var patterns={%s}, host="localhost";window.rays.url=function(name, args, _options){
      var options = _options || {}; var parts   = patterns[name]; var path    = "";
      if(parts.length == 1) { path = parts.join(""); }else{ for(var i = 0, l = args.length; i < l; i++){ path = path + parts[i] + args[i]; } path = path + parts[parts.length-1];}
      var protocol = "http"; if(options.ssl || (!options.ssl && location.protocol == "https:")){ protocol = "https"; }
      var url = protocol+"://"+host+path; if(options.query) { url = url+"?"+options.query } return url;
    };})();"""%(", ".join(v)) == app.generate_javascript_url_builder() for v in patterns])


