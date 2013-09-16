#vim: fileencoding=utf8
from __future__ import print_function
import sys
import types
"""compat.py - Forward compatibility for python2.7, 2.6

Coding guide
============================================

- This module supports >= python3.2 and >= python2.6.
- use `str` for strings
  - If you target python3.2, use `u_()` function to markup unicode strings.
    If not, you can simply markup unicode strings like `u"unicode string"`.
- use `bytes` for bytes
- `range`, `map`, `zip` and `filter` function returns an iterator.
- use `iter_xxx` function to iterate over dictionary objects.
- use `next` function instead of `iterator.next()`.
- use `os.getcedu` function instead of `os.getcwd`.
- Your classes should be extended from `compatobject`.
  - define the method `__str__` which returns `unicode` instead of `__unicode__`.
  - define the method `__truediv__` instead of `__div__`.
  - define the method `__rtruediv__` instead of `__rdiv__`.
  - define the method `__bool__` instead of `__nonzero__`.
  - define the methods `__lt__`, `__eq__` and `__hash__` for comparisons.
  - define the method `__next__` instead of `next`.
- use `compat_import` to import renamed modules.
  - i.e: `compat_import("email.MIMEMultipart", "email.mime.multipart")`
- use `create_urllib_packages` to create python3 compatible urllib modules.

"""

if sys.version_info >= (3,0,0):
  compat_py3 = True
  string_types = (str, bytes)
  integer_types = (int,)
  callable = lambda obj: any("__call__" in k.__dict__ for k in type(obj).__mro__)
  cmp = lambda a, b: (a > b) - (a < b)
  iter_values = lambda v: v.values()
  iter_keys   = lambda v: v.keys()
  iter_items   = lambda v: v.items()
  intern = sys.intern

  def exec_function(object, globals = None, locals = None):
    exec(object, globals or {}, locals or {})
  def reraise(e, v, t):
    raise e(v).with_traceback(t)

  create_urllib_packages = lambda : None
  def compat_import(py2, py3, fromlist=None):
    f = sys._getframe(1)
    if not fromlist:
      exec_function(compile("import "+py3,"<string>","exec"), f.f_globals, f.f_locals)
    else:
      exec_function(compile("from "+py3+" import "+",".join(fromlist),"<string>","exec"), f.f_globals, f.f_locals)

  from functools import reduce
  from imp import reload
  import os
  setattr(os, "getcwdu", os.getcwd)

  im_func = lambda im: im.__func__
  im_self = lambda im: im.__self__
  im_class = lambda im: im.__self__.__class__
  func_attr = lambda func, name: getattr(func, "__"+name+"__")

  method_type = lambda s,f,c: types.MethodType(s, f)

  def import_BytesIO():
    f = sys._getframe(1)
    exec_function(compile("from io import BytesIO","<string>","exec"), f.f_globals, f.f_locals)


  def l_(buf):
    return buf if isinstance(buf, bytes) else buf.encode("latin1")
  def n_(s):
    if isinstance(s, str):
      return s
    elif isinstance(s, bytes):
      return s.decode("latin1")
    return str(s)


else:
  compat_py3 = False
  py2_str = str
  bytes = py2_str
  str   = unicode
  string_types = basestring
  integer_types = (int, long)
  py2_range, py2_map, py2_filter, py2_zip = (range, map, filter, zip)
  range = xrange
  from itertools import imap, ifilter, izip
  map, filter, zip = (imap, ifilter, izip)
  py2_input = input
  input = raw_input
  iter_values = lambda v: v.itervalues()
  iter_keys   = lambda v: v.iterkeys()
  iter_items   = lambda v: v.iteritems()
  next = lambda v: (getattr(v, "next", None) or getattr(v, "__next__"))()
  memoryview = buffer

  eval(compile("""def exec_function(object, globals = None, locals = None):
    exec object in (globals or {}), (locals or {})""", "<exec_function>", "exec"))
  eval(compile("""def reraise(e, v, t):\n  raise e, v, t""", "<reraise>", "exec"))

  def compat_import(py2, py3, fromlist=None):
    import types
    exec_function(compile("import "+py2,"<string>","exec"), globals(), locals())
    py2mod = sys.modules[py2]
    parts = py3.split(".")
    for i in range(len(parts)-1):
      name = ".".join(parts[0:i+1])
      try:
        exec_function(compile("import "+name,"<string>","exec"), globals(), locals())
      except:
        sys.modules[name] = types.ModuleType(name)
    if len(parts) > 1:
      setattr(sys.modules[".".join(parts[:-1])], parts[-1], py2mod)
    if py2.startswith("email"):
      import email
      if isinstance(py2mod, email.LazyImporter): py2mod.__file__
    sys.modules[py3] = py2mod
    f = sys._getframe(1)
    if not fromlist:
      exec_function(compile("import "+py3,"<string>","exec"), f.f_globals, f.f_locals)
    else:
      exec_function(compile("from "+py3+" import "+",".join(fromlist),"<string>","exec"), f.f_globals, f.f_locals)

  def create_urllib_packages():
    import robotparser, urllib, urllib2, urlparse
    all_items = []
    for mod in (urllib, urllib2, urlparse):
      for key in dir(mod):
        if key.startswith("__"): continue
        all_items.append((key, getattr(mod, key)))
    for mod_name in ("request", "parse", "error"):
      name = "urllib."+mod_name
      new_mod = types.ModuleType(name)
      for k, v in all_items: setattr(new_mod, k, v)
      setattr(urllib, mod_name, new_mod)
      sys.modules[name] = new_mod
    setattr(urllib, "robotparser", robotparser)

  im_func = lambda im: im.im_func
  im_self = lambda im: im.im_self
  im_class = lambda im: im.im_class
  func_attr = lambda func, name: getattr(func, "func_"+name)
  method_type = lambda s,f,c: types.MethodType(s, f, c)

  def import_BytesIO():
    f = sys._getframe(1)
    exec_function(compile("from cStringIO import StringIO as BytesIO","<string>","exec"), f.f_globals, f.f_locals)

  def l_(buf):
    return buf
  def n_(s):
    if isinstance(s, bytes):
      return s
    elif isinstance(s, unicode):
      return s.encode("latin1")
    return bytes(s)


def b_(s, encoding='utf8'):
  if isinstance(s, str):
    return s.encode(encoding)
  elif isinstance(s, (integer_types + (float,))):
    return b_(repr(s))
  return bytes(s)
def u_(s, encoding='utf8', errors='strict'):
  return s.decode(encoding, errors) if isinstance(s, bytes) else str(s)

def with_metaclass(metaclass, name, doc = ""):
  klass = metaclass(name, (object, ), {})
  klass.__doc__ = doc
  return klass

class _CompatType(type):
  def __new__(cls, name, bases, attrs):
    if sys.version_info[0] < 3:
      if "__str__" in attrs:
        org_str = attrs["__str__"]
        attrs["__unicode__"] = org_str
        attrs["__str__"] = lambda self: org_str(self).encode(sys.getfilesystemencoding())
      if "__bool__" in attrs      : attrs["__nonzero__"] = attrs["__bool__"]
      if "__floordiv__" in attrs  : attrs["__div__"]     = attrs["__floordiv__"]
      if "__rfloordiv__" in attrs : attrs["__rdiv__"]    = attrs["__rfloordiv__"]
      if "__truediv__" in attrs   : attrs["__div__"]     = attrs["__truediv__"]
      if "__rtruediv__" in attrs  : attrs["__rdiv__"]    = attrs["__rtruediv__"]
    return type.__new__(cls, name, bases, attrs)
compatobject = with_metaclass(_CompatType, "compatobject")
create_urllib_packages()
