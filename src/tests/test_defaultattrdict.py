#vim: fileencoding=utf8
from __future__ import division, print_function

import sys, codecs
from rays import *
from rays.compat import *
from .base import *

import pytest

class TestDefaultAttrDict(Base):
  def test_create(self):
    d = DefaultAttrDict({"a":1, "b":2})
    assert None == d.c
    assert 1 == d.a
    assert 1 == d["a"]
    assert 2 == d.b
    assert 2 == d["b"]
  
    obj = []
    d = DefaultAttrDict({"a":1, "b":2}, lambda: obj)
    assert obj == d.hoge
    assert (repr(d) == "<DefaultAttrDict {'a': 1, 'b': 2, 'hoge': []}>" or
            repr(d) == "<DefaultAttrDict {'a': 1, 'hoge': [], 'b': 2}>" or
            repr(d) == "<DefaultAttrDict {'b': 2, 'a': 1, 'hoge': []}>" or
            repr(d) == "<DefaultAttrDict {'b': 2, 'hoge': [], 'a': 1}>" or
            repr(d) == "<DefaultAttrDict {'hoge': [], 'a': 1, 'b': 2}>" or
            repr(d) == "<DefaultAttrDict {'hoge': [], 'b': 2, 'a': 1}>")
            
  
  def test_setattr(self):
    d = DefaultAttrDict({"a":1, "b":2})
    d.c = "foo"
    assert "foo" == d.c
    assert "foo" == d["c"]
  
  def test_delattr1(self):
    with pytest.raises(AttributeError):
      d = DefaultAttrDict({"a":1, "b":2})
      del d.c
  
  def test_delattr2(self):
    d = DefaultAttrDict({"a":1, "b":2})
    del d.b
    assert None == d.b
    assert None == d["b"]
    del d["a"]
    assert None == d.a
  
  def test_copy(self):
    d = DefaultAttrDict({"a":1, "b":2})
    dc = d.copy()
    assert DefaultAttrDict == dc.__class__
    assert d.a == dc.a
    assert d.b == dc.b
