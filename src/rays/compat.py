#vim: fileencoding=utf8
"""
rays - A "LESS PAIN" lightweight WSGI compatible web framework
===================================================================
Python 2 and 3 compatibility stuff.
"""

import sys, os, types, itertools, functools
version_error = False
if sys.version_info < (3,0,0):
  PY3 = False
  if (2,7,0) > sys.version_info:
    version_error = True
else:
  PY3 = True
  if (3,2,0) > sys.version_info > (3,0,0):
    version_error = True
if version_error:
  sys.stderr.write("rays supports only > 3.2.0 or > 2.7.0")
  sys.exit(1)

if PY3:
  unicode = str
  string_types = (unicode, bytes)
  integer_types = (int,)

  irange  = range
  imap    = map
  ifilter = filter
  izip    = zip
  reduce  = functools.reduce

  raw_input = input
  callable = lambda v: hasattr(v, "__call__")
  cmp = lambda a, b: (a > b) - (a < b)
  iter_values = lambda v: v.values()
  iter_keys   = lambda v: v.keys()
  iter_items   = lambda v: v.items()

  im_self = lambda func: getattr(func, '__self__', None)
  im_func = lambda func: getattr(func, '__func__', None)
  im_class = lambda func: getattr(func, '__class__', None)

  method_type = lambda s,f,c: types.MethodType(s, f)

  getcwd = os.getcwd
  def exec_function(object, globals = None, locals = None):
    exec(object, globals or {}, locals or {})
  def reraise(e, v, t):
    raise e(v).with_traceback(t)
  def l_(buf):
    return buf if isinstance(buf, bytes) else buf.encode("latin1")
  def n_(s):
    if isinstance(s, unicode):
      return s
    elif isinstance(s, bytes):
      return s.decode("latin1")
    return unicode(s)

  from urllib.parse import urljoin, parse_qsl, SplitResult as UrlSplitResult
  from urllib.parse import urlencode, quote as urlquote, unquote as urlunquote
  from http.cookies import SimpleCookie
  import pickle
  from io import BytesIO

else:
  bytes = str
  string_types = basestring
  integer_types = (int, long)

  irange  = xrange
  imap    = itertools.imap
  ifilter = itertools.ifilter
  izip    = itertools.izip

  iter_values = lambda v: v.itervalues()
  iter_keys   = lambda v: v.iterkeys()
  iter_items   = lambda v: v.iteritems()

  im_self = lambda func: getattr(func, 'im_self', None)
  im_func = lambda func: getattr(func, 'im_func', None)
  im_class = lambda func: getattr(func, 'im_class', None)

  method_type = lambda s,f,c: types.MethodType(s, f, c)

  getcwd = os.getcwdu
  eval(compile("""\
def exec_function(object, globals = None, locals = None):
    exec object in (globals or {}), (locals or {})
""",
    "<exec_function>", "exec"
  ))
  eval(compile("""\
def reraise(e, v, t):
  raise e, v, t
""",
    "<reraise>", "exec"
  ))
  def l_(buf):
    return buf
  def n_(s):
    if isinstance(s, bytes):
      return s
    elif isinstance(s, unicode):
      return s.encode("latin1")
    return bytes(s)

  from urlparse import urljoin, parse_qsl, SplitResult as UrlSplitResult
  from urllib import urlencode, quote as urlquote, unquote as urlunquote
  from Cookie import SimpleCookie
  try:
    import cPickle as pickle
  except ImportError:
    import pickle
  try:
    from cStringIO import StringIO as BytesIO
  except ImportError:
    from StringIO import StringIO as BytesIO

def b_(s, encoding='utf8'):
  if isinstance(s, unicode):
    return s.encode(encoding) 
  elif isinstance(s, (integer_types + (float,))):
    return b_(repr(s))
  return bytes(s)
def u_(s, encoding='utf8', errors='strict'):
  return s.decode(encoding, errors) if isinstance(s, bytes) else unicode(s)
def with_metaclass(metaclass, name, doc = ""):
  klass = metaclass(name, (object, ), {})
  klass.__doc__ = doc
  return klass
