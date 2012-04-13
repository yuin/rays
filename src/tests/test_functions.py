#vim: fileencoding=utf8
from __future__ import division, print_function

import sys, codecs
from rays import *
from rays.compat import *
from .base import *

import pytest

class TestFunctions(Base):
  def test_return_response(self):
    with pytest.raises(ReturnResponse):
      return_response("test")
  
  def test_eval_thunk(self):
    assert "value" == eval_thunk(lambda : "value")
    assert "value" == eval_thunk("value")
  
  def test_cached_property(self):
    class A(PropertyCachable):
      """A class

        :Attributes:
            count
                docs
      """
      def __init__(self, id):
        self.count = 0
        self.id = id
  
      @cached_property
      def value(self):
        """docs"""
        self.count += 1
        return "%s%d"%(self.__class__.__name__, self.id)
  
    class B(A): 
      pass
  
    a1 = A(1)
    a2 = A(2)
    b1 = B(1)

    assert A.__doc__.strip() == """A class

        :Attributes:
            count
                docs
            value
                docs"""
  
    assert "A1" == a1.value
    assert "A1" == a1.value
    assert 1 == a1.count
  
    assert "A2" == a2.value
    assert "A2" == a2.value
    assert 1 == a2.count
  
    assert "B1" == b1.value
    assert "B1" == b1.value
    assert 1 == b1.count
  
  def test_tls_property(self):
    import threading
  
    class A(object):
      def __init__(self):
        self.tls = threading.local()
  
      value = tls_property("value", "doc")
  
    a = A()
    a.value = 1
    assert 1 == a.value
    assert 1 == a.tls.value
    assert "(Thread Local) doc" == A.value.__doc__
  
  def test_quess_decode(self):
    assert u_("あああ") == guess_decode(u_("あああ").encode("cp932"))
    assert u_("あああ") == guess_decode(u_("あああ").encode("euc_jp"))
    assert u_("あああ") == guess_decode(u_("あああ").encode("shift_jis"))
    assert u_("あああ") == guess_decode(u_("あああ").encode("utf8"))
    assert u_("") == guess_decode(None)
    with pytest.raises(UnicodeError):
      print(guess_decode(2))

  
  def test_escape_html(self):
    assert u_("&amp;&lt;&gt;&#39;&quot;") == escape_html(u_("&<>'\""))
  
  def test_unescape_html(self):
    assert u_("&<>'\"") == unescape_html(u_("&amp;&lt;&gt;&#39;&quot;"))
  
  def test_to_http_date_string(self):
    from datetime import datetime
  
    date = datetime(2010, 1, 1, 1, 0, 0)
    assert "Fri, 01 Jan 2010 01:00:00 GMT" == to_http_date_string(date)
    assert "Fri, 01 Jan 2010 01:00:00 GMT" ==  to_http_date_string(date.timetuple())
  
  def test_snake_case(self):
    assert "test_model" == to_snake_case("TestModel")
    assert "test_model" == to_snake_case("TESTModel")
  
