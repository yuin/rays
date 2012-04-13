#vim: fileencoding=utf8
from __future__ import division, print_function

import sys, codecs
from rays import *
from rays.compat import *
from .base import *

import pytest

class TestHookable(Base):
  def test_add_hook_func(self):
    p = Hookable()
    p.add_hook("test0", lambda v: v, name="hook1")
    p.add_hook("test0", lambda v: v, name="hook3", pos="first")
    p.add_hook("test0", lambda v: v, name="hook5", pos="after_hook2")
    p.add_hook("test0", lambda v: v, name="hook4", pos="before_hook2")
    p.add_hook("test0", lambda v: v, name="hook2")
  
    p.add_hook("test1", lambda v: v, name="hook6", pos="after_hook2")
    p.add_hook("test1", lambda v: v, name="hook7", pos="first")
    p.add_hook("test1", lambda v: v, name="hook8", pos="last")
    p.add_hook("test1", lambda v: v, name="hook9")
  
    p.add_hook("test2", lambda v: v, name="hook10", pos="last")
    p.add_hook("test2", lambda v: v, name="hook11", pos="before_hook10")
    p.add_hook("test2", lambda v: v, name="hook12", pos="before_hook10")
    p.add_hook("test2", lambda v: v, name="hook13", pos="after_hook10")
    p.add_hook("test2", lambda v: v, name="hook14", pos="after_hook10")
  
    hooks = p.hooks["test0"]
    assert repr(hooks[0]).startswith("<rays.Hook ")
    assert "hook3" == hooks[0].name
    assert "hook1" == hooks[1].name
    assert "hook4" == hooks[2].name
    assert "hook2" == hooks[3].name
    assert "hook5" == hooks[4].name
  
    hooks = p.hooks["test1"]
    assert "hook7" == hooks[0].name
    assert "hook6" == hooks[1].name
    assert "hook9" == hooks[2].name
    assert "hook8" == hooks[3].name
  
    hooks = p.hooks["test2"]
    assert "hook11" == hooks[0].name
    assert "hook12" == hooks[1].name
    assert "hook10" == hooks[2].name
    assert "hook13" == hooks[3].name
    assert "hook14" == hooks[4].name
  
  def test_add_hook_by_decorator(self):
  
    p = Hookable()
  
    @p.hook("test0")
    def hook1(v):
      pass
  
    @p.hook("test0", pos="first")
    def hook2(v):
      pass
  
    @p.hook(pos="before_hook2")
    def on_test0(v):
      pass
  
    hooks = p.hooks["test0"]
    assert "on_test0" == hooks[0].name
    assert "hook2" == hooks[1].name
    assert "hook1" == hooks[2].name
  
  def test_remove_hook(self):
    p = Hookable()
  
    @p.hook("test0")
    def test1():
      return 1
  
    @p.hook("test0")
    def test2():
      return 2
  
    p.remove_hook("test0", test1)
    hooks = p.hooks["test0"]
    assert 1 == len(hooks)
    assert "test2" == hooks[0].name
  
  def test_run_hook(self):
    p = Hookable()
  
    @p.hook("test0")
    def test1():
      return 1
  
    @p.hook("test0")
    def test2():
      return 2
  
    @p.hook("test1")
    def test3():
      return 3
  
    result = p.run_hook("test0")
    assert [1,2] == result
    result = p.reverse_run_hook("test0")
    assert [2,1] == result

    # do nothing
    result = p.reverse_run_hook("dummy")
  
  def test_hookable_class(self):
    
    class A(HookableClass): pass
    class B(A): pass
  
    A.add_hook("test0", lambda v: v, name="hook1")
    B.add_hook("test0", lambda v: v, name="hook2")
  
    hooks = A.hookable.hooks["test0"]
    assert "hook1" == hooks[0].name
    assert 1 == len(hooks)
  
    hooks = B.hookable.hooks["test0"]
    assert "hook2" == hooks[0].name
    assert 1 == len(hooks)
