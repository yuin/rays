#vim: fileencoding=utf8
from __future__ import division, print_function

import sys, os.path, codecs, traceback
from rays import *
from rays.compat import *
from .base import *

import pytest

class TestEmbpy(Base): # {{{
  def template(self, name):
    return os.path.join(self.TEST_DIR, "templates", name)
  def cache(self, name):
    return os.path.join(self.TEST_DIR, "templates", "caches", name)
  def clear_caches(self):
    for v in os.listdir( os.path.join(self.TEST_DIR, "templates", "caches")):
      os.remove(os.path.join(self.TEST_DIR, "templates", "caches", v))

  def setup_method(self, method):
    try:
      os.mkdir(os.path.join(self.TEST_DIR, "templates", "caches"))
    except:
      pass
    Base.setup_method(self, method)
    self.clear_caches()
    return 

  def teardown_method(self, method):
    Base.teardown_method(self, method)
    self.clear_caches()
    try:
      os.rmdir(os.path.join(self.TEST_DIR, "templates", "caches"))
    except:
      pass
    return 

  def test_set_and_get_template_globals(self):
    embpy = Embpy(codecs.open(self.template("index.html")),
                  self.cache("index.html"),
                  {"global_value": "global"})
    assert {"u_":u_, "b_":b_, "n_":n_, "global_value":"global"} == embpy.template_globals

  def test_render_without_filter(self):
    embpy = Embpy(codecs.open(self.template("index.html")),
                  self.cache("index.html"))
    assert u_("""<div>
    値1
        値2
    
</div>
<div>
    <p>value1</p>
    
</div>
""") == embpy.render({"text_values": [u_("値1"), u_("値2")],
                             "html_values": [u_("<p>value1</p>")]})
    return embpy

  def test_cache(self):
    embpy = self.test_render_without_filter()
    assert embpy.is_cached()
    self.test_render_without_filter()
    data = open(self.template("index.html"), "rb").read()
    open(self.template("index.html"), "wb").write(data)
    assert (not embpy.is_cached())
    self.test_render_without_filter()

  def test_render_with_filter(self):
    def filter(s):
      return "filtered_"+s
    embpy = Embpy(codecs.open(self.template("index.html")),
                  self.cache("index.html"), filter = filter)
    assert u_("""<div>
    filtered_値1
        filtered_値2
    
</div>
<div>
    <p>value1</p>
    
</div>
""") == embpy.render({"text_values": [u_("値1"), u_("値2")],
                             "html_values": [u_("<p>value1</p>")]})

  def test_compound_statements(self):
    embpy = Embpy(codecs.open(self.template("compound_statements.html")),
                  self.cache("compound_statements.html"), encoding="cp932")
    assert u_("""    表示される(SJIS)

    while

""") == embpy.render()

  def test_syntax_error(self):
    embpy = Embpy(codecs.open(self.template("syntax_error.html")),
                  self.cache("syntax_error.html"))
    try:
      embpy.render({"text_values":[]})
      assert False
    except SyntaxError as e:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      output = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
      assert "File \"<string>\", line 6" in output
      
  def test_occur_errors_in_rendering(self):
    embpy = Embpy(codecs.open(self.template("index.html")),
                  self.cache("index.html"))
    try:
      embpy.render() # <= template values does not given by the caller
    except NameError as e:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      output = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
      print(output)
      assert "File \"<string>\", line 6" in output
      assert "NameError: name 'text_values' is not defined" in output
    else:
      assert False
# }}}

class TestRendererAndHelper(Base):
  TEMPLATE_DIR = os.path.join(Base.TEST_DIR, "templates")
  CACHE_DIR    = os.path.join(Base.TEST_DIR, "templates", "caches")

  def clear_caches(self):
    if os.path.exists(self.CACHE_DIR):
      for v in os.listdir(self.CACHE_DIR):
        os.remove(os.path.join(self.CACHE_DIR, v))
    else:
      os.mkdir(self.CACHE_DIR)

  def setup_method(self, method):
    Base.setup_method(self, method)
    self.clear_caches()
    return 

  def teardown_method(self, method):
    Base.teardown_method(self, method)
    self.clear_caches()
    return 

  def test_render_file(self):
    renderer = Renderer(self.TEMPLATE_DIR, self.CACHE_DIR)
    assert u_("""<div>
    値1
        値2
    
</div>
<div>
    <p>value1</p>
    
</div>
""") == renderer.render_file("index", {"text_values": [u_("値1"), u_("値2")],
                             "html_values": [u_("<p>value1</p>")]})

  def test_render_file_with_encoding(self):
    renderer = Renderer(self.TEMPLATE_DIR, self.CACHE_DIR)
    assert u_("""    表示される(SJIS)

    while

""") == renderer.render_file("compound_statements", encoding="cp932")

  def test_render_string(self):
    renderer = Renderer(self.TEMPLATE_DIR, self.CACHE_DIR)
    assert u_("""文字:あ""") == renderer.render_string(u_("""文字:<%= v %>"""), {"v": u_("あ")})

  def test_render_with_layouts(self):
    renderer = Renderer(self.TEMPLATE_DIR, self.CACHE_DIR)
    assert u_("""<body>
<h1>layout test</h1>
<div>body</div>

</body>

""") == renderer.contents({})
    

  def test_capture(self):
    renderer = Renderer(self.TEMPLATE_DIR, self.CACHE_DIR)
    assert u_("""
連結
<div>
  
  ok

</div>
""") == renderer.capture_outputs({})

  def test_htmlquote(self):
    h = Helper()
    assert u_("&amp;&lt;&gt;&#39;&quot;") == h.htmlquote(u_("&<>'\""))
    assert u_("&amp;&lt;&gt;&#39;&quot;") == Helper.htmlquote(u_("&<>'\""))


