#vim: fileencoding=utf8
"""
rays - A "LESS PAIN" lightweight WSGI compatible web framework
===================================================================

Licence (MIT)
-------------
 
Copyright (c) 2009-2012, Yusuke Inuzuka.
 
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from __future__ import division, print_function
from .compat import *

import re, cgi, traceback, threading, os, os.path, mimetypes, types
import time, collections, contextlib, codecs, marshal, functools, inspect
import logging, json
from datetime import datetime, timedelta
from hashlib import sha1

import urllib.parse
compat_import(py3="http.cookies", py2="Cookie")
compat_import(py3="pickle", py2="cPickle")
import_BytesIO()

__author__ = "Yusuke Inuzuka"
__version__ = "0.4.2"
__license__ = 'MIT'

# core utilities {{{
# functions {{{
def return_response(f):
  """Sends a response to a browser immediately."""
  raise ReturnResponse(f)

def eval_thunk(maybe_thunk):
  """ """
  if callable(maybe_thunk):
    return maybe_thunk()
  else:
    return maybe_thunk 

class _CachedProperty(object):
  def __init__(self, f):
    self.f = f
    self.__name__ = f.__name__
    self.__doc__ = f.__doc__

class CachedProperty(_CachedProperty):
  def __get__(self, ins, klass):
    value = self.f(ins)
    setattr(ins, self.__name__, value)
    return value

class PropertyCachableType(type):
  def __new__(cls, name, bases, dct):
    cached_property_docs = []
    for k, v in iter_items(dct.copy()):
      if isinstance(v, _CachedProperty):
        if v.__doc__:
          cached_property_docs.append((v.__name__, v.__doc__))
        dct[k] = CachedProperty(v.f)
    cls = type.__new__(cls, name, bases, dct)
    if cls.__doc__:
      m = re.search("\s+", cls.__doc__.strip().split("\n")[-1])
      if m:
        indent = len(m.group(0))
      else:
        indent = 4
      buffer = [cls.__doc__.strip()]
      for name, doc in cached_property_docs:
        buffer.append((" "*(indent-4)) + name)
        buffer.append((" "*indent) + "".join(doc.split("\n")))
      cls.__doc__ = "\n".join(buffer)
    return cls

PropertyCachable = with_metaclass(PropertyCachableType, "PropertyCachableType", 
  """Base class that provides a convenient way to cache method results. """
)

def cached_property(f):
  """ """
  return _CachedProperty(f)

def tls_property(name, doc = u_("")):
  """ """
  def fget(self): return getattr(self.tls, name, None)
  def fset(self, value): setattr(self.tls, name, value)
  return property(fget, fset, None, "(Thread Local) %s"%doc)

def guess_decode(q ,lst = ["utf_8", "euc_jp", "cp932", "shift_jis"]):
  """ """
  if not q:
    return u_("")
  if isinstance(q, str):
    return q
  for codec in lst:
    try:
      return q.decode(codec)
    except:
      pass
  raise UnicodeError(q)

def unquote_guess_decode(q):
  """ """
  return guess_decode(urllib.parse.unquote(q))

_htmlentity_trans_table = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("'", "&#39;"), ('"', "&quot;"))
_htmlentity_trans_table_rev = list(map(lambda v: (v[1], v[0]), _htmlentity_trans_table))

def _trans(s, table):
  return reduce(lambda r,v: r.replace(v[0], v[1]), table, s)

def escape_html(s):
  """ """
  return _trans(s, _htmlentity_trans_table)

def unescape_html(s): 
  """ """
  return _trans(s, _htmlentity_trans_table_rev)

def to_http_date_string(date): 
  """ """
  format = "%a, %d %b %Y %H:%M:%S GMT"
  if isinstance(date, datetime):
    return date.strftime(format)
  return time.strftime(format, date)

def parse_http_date_string(string): 
  """ """
  return datetime(*time.strptime(string.replace("GMT", "+0000"), "%a, %d %b %Y %H:%M:%S +0000")[:6])

def to_snake_case(s, pat=[]):
  """ """
  if not pat:
    pat.append(re.compile(r"(\B[A-Z][^A-Z])"))
  return pat[0].sub(r'_\1', s).lower()
# }}}

class ClassInitableType(type): # {{{
  """Metaclass that provides a convenient way to initialize classes.

  You can define a class_init(cls) method, which will be called when the class is created.
  """
  def __new__(cls, name, bases, dct):
    if "class_init" in dct:
      dct["class_init"] = staticmethod(dct["class_init"])
    cls = type.__new__(cls, name, bases, dct)
    if hasattr(cls, "class_init"):
      cls.class_init(cls)
    return cls
# }}}

# {{{ ClassInitableType 
ClassInitable = with_metaclass(ClassInitableType, "ClassInitable", 
  """Base class that provides a convenient way to initialize classes.

  You can define a class_init(cls) method, which will be called when the class is created.
  """
)
# }}}

class Hook(PropertyCachable): # {{{
  NONE   = -1
  BEFORE = 0
  AFTER  = 1
  FIRST  = 2
  LAST   = 3

  def __init__(self, hookable, func, type, name, pos, id):
    self.hookable = hookable
    self.func = func
    self.type = type
    self.name = name
    self.pos  = pos
    self.id   = id

  def __repr__(self):
    return "<rays.Hook %s>"%(repr(self.__dict__))

  @cached_property
  def pos_type(self):
    if self.pos.startswith("before_"):
      return self.BEFORE
    if self.pos.startswith("after_"):
      return self.AFTER
    if self.pos == "first":
      return self.FIRST
    if self.pos == "last":
      return self.LAST
    return self.NONE

  @cached_property
  def pos_name(self):
    if self.pos_type == self.BEFORE:
      return self.pos[7:]
    if self.pos_type == self.AFTER:
      return self.pos[6:]
    return ""

  @cached_property
  def is_pos_type_before(self): return self.pos_type == self.BEFORE

  @cached_property
  def is_pos_type_after(self): return self.pos_type == self.AFTER

  @cached_property
  def is_pos_type_first(self): return self.pos_type == self.FIRST

  @cached_property
  def is_pos_type_last(self): return self.pos_type == self.LAST

  def __call__(self, *a, **kw):
    return self.func(*a, **kw)

  def __lt__(self, other):
    return self.__cmp__(other) < 0

  def __cmp__(self, other):
    if self.name == other.pos_name:
      if other.is_pos_type_before:
        return 1
      if other.is_pos_type_after:
        return -1
    elif other.name == self.pos_name:
      if self.is_pos_type_before:
        return -1
      if self.is_pos_type_after:
        return 1
    elif self.pos_name and self.pos_name == other.pos_name:
      if self.is_pos_type_before and other.is_pos_type_after:
          return -1
      if other.is_pos_type_before and self.is_pos_type_after:
          return 1
    elif self.is_pos_type_last and not other.is_pos_type_last:
      return 1
    elif self.is_pos_type_first and not other.is_pos_type_first:
      return -1
    elif not self.is_pos_type_last and other.is_pos_type_last:
      return -1
    elif not self.is_pos_type_first and other.is_pos_type_first:
      return 1
    elif not self.pos and other.pos:
      ref = self.hookable.get_hook_by_type_and_name(self.type, other.pos_name)
      if ref:
        return cmp(self, ref)
    elif self.pos and not other.pos:
      ref = self.hookable.get_hook_by_type_and_name(self.type, self.pos_name)
      if ref:
        return cmp(ref, other)

    return cmp(self.id, other.id)
# }}}

class Hookable(object): # {{{
  """Hookable object support.

  """
  
  def __init__(self):
    self.hooks    = collections.defaultdict(list)
    self.hook_map = collections.defaultdict(lambda : {})

  def get_hook_by_type_and_name(self, hook_type, name):
    """Returns a named Hook object associated with ``hook_type``."""
    return self.hook_map[hook_type].get(name, None)

  def add_hook(self, hook_type, hook=None, pos="", name=""):
    """Adds a hook to the object. 
    
    :Parameters:
        pos
            The hooks position in relation to other hooks. 
            ``pos`` can consist of a few different values

                - The special strings: ``"first"``, ``"last"``
                - ``"before_"`` followed by other extension name.(i.e. before_DatabaseExtension)
                - ``"after_"`` followed by other extension name.(i.e. after_DatabaseExtension)
    """
    hook = Hook(self, hook, hook_type, name or hook.__name__, pos, len(self.hooks[hook_type]))
    self.hook_map[hook_type][hook.name] = hook
    self.hooks[hook_type].append(hook)
    self.hooks[hook_type].sort()

  def hook(self, hook_type="", pos="", name=""):
    """Adds a hook to the object. 
    
    This method is suitable to use as a decorator.
    """
    def _(f):
      self.add_hook(hook_type or f.__name__[3:], f, pos, name)
      return f
    return _

  def remove_hook(self, hook_type, hook):
    """Remove a hook."""
    self.hooks[hook_type] = [h for h in self.hooks[hook_type] if h.func != hook]

  def _run_hook(self, hook_type, args, kw, f=lambda x:x):
    if hook_type not in self.hooks: 
      return
    return [hook(*args, **kw) for hook in f(self.hooks[hook_type])]

  def run_hook(self, hook_type, args = [], kw = {}):
    """Runs hooks associated with ``hook_type``."""
    return self._run_hook(hook_type, args, kw)
 
  def reverse_run_hook(self, hook_type, args = [], kw = {}):
    """Runs hooks associated with ``hook_type`` in the reverse order."""
    return self._run_hook(hook_type, args, kw, reversed)

def __create_hookable_class():
  class HookableClass(Hookable, ClassInitable):
    def class_init(cls):
      cls.hookable = Hookable()

  class Delegate(object):
    def __init__(self, name):
      self.name = name
    def __get__(self, ins, klass):
      return getattr(klass and klass.hookable or ins.__class__.hookable, self.name)

  hookable = Hookable()
  for name, method in inspect.getmembers(hookable):
    if inspect.ismethod(method):
      name = method.__name__
      if im_self(method) == hookable and name[:2] != "__":
        setattr(HookableClass, name, Delegate(name))
  return HookableClass
HookableClass = __create_hookable_class()
HookableClass.__doc__ = """ Hookable class support.  """

# }}}

class DefaultAttrDict(collections.defaultdict): # {{{
  """A defaultdict like object, whose items also be accessible through object attributes.
  """
  def __init__(self, dct = None, factory = None):
    super(DefaultAttrDict, self).__init__(factory or (lambda : None))
    self.update(dct or {})

  def __repr__(self):
    return '<DefaultAttrDict ' + dict.__repr__(self) + '>'

  def __getattr__(self, key):
    return self[key]

  def __setattr__(self, key, value):
    self[key] = value

  def __delattr__(self, key):
    try:
      del self[key]
    except KeyError as e:
      raise AttributeError(e)

  def copy(self):
    d = {}
    for k, v in iter_items(self): d[k] = v
    return DefaultAttrDict(d, self.default_factory)
# }}}
  
class ReturnResponse(Exception): # {{{
  def __init__(self, f):
    self.thunk = f
# }}}

class Abort(ReturnResponse): # {{{
  def __init__(self, f, status):
    self.thunk = f 
    self.status  = status
# }}}
# }}}

class Action(PropertyCachable): # {{{
  """Action.

  :Attributes:
      param_types     
          URL parameter types
      name
          Action name
      path_pattern
          URL pattern string
  """

  PARAM_REGEX = re.compile("\((\w+:)")
  def __init__(self, app, func):
    self.app = app
    self.func = func
    self.filters = []
    self.method = "get"
    self.path_pattern = ""

  @cached_property
  def param_types(self):
    return list(map(lambda s: eval(s[:-1]), 
      self.PARAM_REGEX.findall(self.full_path_pattern) or []))

  @cached_property
  def full_path_pattern_compiled(self):
    pattern = u_("(").join(self.PARAM_REGEX.split(self.full_path_pattern)[::2])
    return re.compile("^%s$"%pattern)

  @cached_property
  def name(self):
    return self.func.__name__

  @cached_property
  def full_path_pattern(self):
    return self.app.base + self.path_pattern

  def match(self, str):
    """Returns a MatchObject object if the given string match the path pattern, Otherwise None.
    """
    return self.full_path_pattern_compiled.match(str)

  def append_filter(self, filter):
    """Adds a ``filter`` to the action as a filter."""
    self.filters.append(filter)

  def __call__(self, *a, **kw):
    """Performs this action without filters.
    """
    self.app.res.content = self.func(*a, **kw)
    return self.app.res.content

  def perform_with_filters(self, *a, **kw):
    """Performs this action with filters.
    """
    generators = [filter(*a, **kw) for filter in self.filters]
    for generator in generators:
      next(generator)
    self.app.res.content = self.func(*a, **kw)
    for generator in reversed(generators):
      try:
        next(generator)
      except StopIteration:
        pass
    return self.app.res.content
# }}}

class Application(Hookable): # {{{
  """Application to dispatch requests based on HTTP methods and path.

  An Application object is a WSGI callable object.

  :Attributes:
      base     
          URL base path
      charset 
          Character encoding that this application uses
      debug
          If this member is True, rays prints verbose message on its bevavior and 
          An autoreload feature is enabled in ``run_xxx()`` methods.
      host
          Host name such as "localhost"
      ext
          Namespace for extensions
      vars
          rays.DefaultAttrDict object, an user namespace for application global variables.
      req
          (Thread local) rays.Request object.
      res
          (Thread local) rays.Response object.
  """
  def __init__(self, base='/', charset="UTF-8", debug=False):
    self.initialize()
    self.base = base
    self.charset = charset
    self.debug = debug
    self.logger = logging.getLogger("rays")
    self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    self.logger.addHandler(ch)

    self.url = type('_', (), {"__getattr__" : lambda s,v : lambda *a, **kw : self._url(v, *a, **kw)})()
    self.initialize_lock = threading.Lock()

  def initialize(self):
    self.current_filters = []
    self.error_handlers = {}
    self.actions = []
    self.actions_map = {}
    self.url_cache = {}
    self.initialized = False
    self._renderer = None
    self.vars = DefaultAttrDict()
    self.ext = DefaultAttrDict()
    self.tls = threading.local()
    self.tls_names = set([])
    super(Application, self).__init__()

  def define_tls_property(self, name, doc):
    """Defines a thread local property on this object."""
    self.tls_names.add(name)
    setattr(self.__class__, name, tls_property(name, doc))

  def copy_tls_property(self, dct = None):
    """Copies thread local data to a dictionary.
        rays.Applicaion object holds thread local data whose 
        values are request specific.
        If you need to create child threads in a HTTP request, you must
        copy these data to the child threads.

        >>> def make_worker(tls):
        ...   def run():
        ...     app.copy_tls_property(tls)
        ...     # operations...
        ...   return run
        ... @app.get("index")
        ... def index():
        ...   t = threading.Thread(target=make_worker(app.copy_tls_property()))
        ...   t.start()
        ...   t.join()

    """
    if dct is None:
      result = {}
      for k in self.tls_names:
        result[k] = getattr(self, k)
      return result
    else:
      for k in self.tls_names:
        setattr(self, k , dct[k])

  def get_renderer(self):
    if not self._renderer:
      self._renderer = Renderer("./templates", "./caches", template_globals = {"app":self}, filter = Helper.htmlquote, encoding="utf8")
    return self._renderer

  def set_renderer(self, value):
    self._renderer = value

  renderer = property(get_renderer, set_renderer, None, """rays.Renderer object""")

  def config(self, name, value=None, frame=None):
    """Sets the valule for the configurations.

    :Available configuration parameters:
        - base(str)
        - charset(str)
        - debug(Boolean)
        - logger : logging.Logger object( in the Python standard libraries )
        - renderer : dict
            - template_dir : str, default ``"./templates"``
            - cache_dir    : str, default ``"./caches"``
            - template_globals : dict
            - encoding : str, default ``utf8``
        - ExtensionLoader: dict
            - module : extension module object, See Extension documentations for further details.
    """
    if isinstance(name, (list, tuple)):
      f = sys._getframe(1)
      return [self.config(k,v,f) for k,v in name]

    if name in ("base","charset", "debug", "logger"):
      setattr(self, name, value)

    elif name == "ExtensionLoader":
      ExtensionLoader(self, value["module"]).load()

    elif name.endswith("Extension"):
      try:
        klass = eval(name)
      except:
        f = frame or sys._getframe(1)
        klass = eval(name, f.f_globals, f.f_locals)
      klass.app_config(self, value)

    elif name == "renderer":
      for k,v in iter_items(value):
        setattr(self.renderer, k, v)

    else:
      setattr(self.vars, name, value)

  def helper(self, f):
    """Adds a helper function to the renderer.

    This method is suitable to use as a decorator.
    """
    helper = self.renderer.template_globals["h"]
    setattr(helper, f.__name__, method_type(f, helper, helper.__class__))
    return f

  def init_routes(self):
    self.actions_map = {}
    self.url_cache = {}
    for action in self.actions:
      self.actions_map[action.name] = action

  def get(self, pattern):
    """ Binds a function to a GET request path. """
    return self.route(pattern, "get")
  def post(self, pattern):
    """ Binds a function to a POST request path. """
    return self.route(pattern, "post")
  def put(self, pattern): 
    """ Binds a function to a PUT request path. """
    return self.route(pattern, "put")
  def delete(self, pattern):
    """ Binds a function to a DELETE request path. """
    return self.route(pattern, "delete")
  def head(self, pattern): 
    """ Binds a function to a HEAD request path. """
    return self.route(pattern, "head")

  def route(self, pattern, method="get"):
    """Adds a route."""
    def _(f):
      if not isinstance(f, Action):
        f = Action(self, f)
      f.method = method
      f.path_pattern = pattern
      for filter in self.current_filters:
        if isinstance(filter, (list, tuple)):
          excepts = filter[1].get("except",[])
          if f.name in excepts or f.func in excepts: continue
          filter = filter[0]
        f = self.apply_filter(filter)(f)
      self.actions.append(f)
      return f
    return _

  def apply_filter(self, filter_func):
    """Adds a ``filter_func`` to a decorated action as a filter."""
    def _(f):
      if isinstance(f, Action):
        f.append_filter(filter_func)
      else:
        f = Action(self, f)
        f.append_filter(filter_func)
      return f
    return _

  @contextlib.contextmanager
  def filter(self, *filter_funcs):
    """Adds ``filter_funcs`` to the current routing context as a filter.

    This method can be used as context managers for a ``with`` statement.
    """
    index = len(self.current_filters)
    size = len(filter_funcs)
    self.current_filters.extend(filter_funcs)
    yield
    del self.current_filters[index:index+size]

  def error(self, code):
    """Adds the decorated function to this application as a error handler."""
    def _(f):
      self.error_handlers[code] = f
      return f
    return _

  def get_url_builder(self, name):
    """Returns a url builder for the given named route."""
    if name not in self.url_cache:
      parts = re.compile("\([^\)]+\)").split(self.actions_map[name].full_path_pattern)
      def encode(v):
        try:
          return urllib.parse.quote(v.encode(self.charset))
        except:
          return u_(v)
      def mkclosure(parts):
        def _(*args, **kw):
          _query = kw.get("_query", None)
          _ssl   = kw.get("_ssl", None)
          if len(parts) == 1:
            path = "".join(parts)
          else:
            a = list(map(encode, args))
            path = "".join(map(lambda p:p[0]+p[1], zip(parts,a+[""])))
          if _ssl or (_ssl is None and self.req.is_ssl):
            protocol = "https"
          else:
            protocol = "http"
          url = "%s://%s%s"%(protocol, self.host, path)
          if _query:
            return url + "?" + _query
          else:
            return url
        return _
      self.url_cache[name] = mkclosure(parts)
    return self.url_cache[name] 

  def _url(self, name, *args, **kw):
    return self.get_url_builder(name)(*args, **kw)

  def generate_javascript_url_builder(self, names = None):
    """Returns javascript code which allows client side code to generate application urls."""
    names = names or list(iter_keys(self.actions_map))
    result = []
    code   = []
    result.append("if(typeof(rays) == 'undefined'){ window.rays={};}");
    patterns = {}
    for name in names:
      patterns[name] = re.compile("\([^\)]+\)").split(self.actions_map[name].full_path_pattern)
    code.append("var patterns=%s, host=\"%s\";"%(json.dumps(patterns), self.host))
    code.append("""window.rays.url=function(name, args, _options){
      var options = _options || {}; var parts   = patterns[name]; var path    = "";
      if(parts.length == 1) { path = parts.join(""); }else{ for(var i = 0, l = args.length; i < l; i++){ path = path + parts[i] + args[i]; } path = path + parts[parts.length-1];}
      var protocol = "http"; if(options.ssl || (!options.ssl && location.protocol == "https:")){ protocol = "https"; }
      var url = protocol+"://"+host+path; if(options.query) { url = url+"?"+options.query } return url;
    };""");
    result.append("(function(){%s})();"%("".join(code)))
    return "".join(result)

  def __call__(self, env, start_response):
    """ WSGI callable method."""
    if not self.initialized:
      with self.initialize_lock:
        if not self.initialized:
          self.define_tls_property("req", "rays.Request object")
          self.define_tls_property("res", "rays.Response object")
          self.host = env["HTTP_HOST"]
          self.run_hook("before_initialize")
          self.init_routes()
          self.initialized = True
          self.run_hook("after_initialize")

    self.run_hook("before_call", [env, start_response])
    response = Response(start_response)
    response.charset = self.charset
    response.content = ""
    
    try:
      request = Request(env)
      self.req = request
      self.res = response
      path, method = request.path, request.method

      self.run_hook("before_dispatch")
      find = False
      for action in self.actions:
        m = action.match(path)
        if m:
          find = True
          if action.method != method:
            continue
          params = list(map(lambda s: s[1](guess_decode(l_(s[0]))), zip(m.groups(), action.param_types)))
          request.action = action
          request.params = params
          self.run_hook("before_action")
          return_response(request.action.perform_with_filters(*request.params))
      if find:
        response.method_not_allowed()
      else:
        response.notfound()
    except Exception as e:
      self._handle_exception(response, e)

    # gevent.WebSocketHandler passes None as a start_response function
    if start_response is None: return

    return self._send_back_response(response)

  def _handle_exception(self, response, e):
    if isinstance(e, Abort):
      response.exception = e
      try:
        response.content = eval_thunk(e.thunk or 
          self.error_handlers.get(int(e.status.split(" ")[0]), lambda : e.status)())
      except ReturnResponse as e2:
        response.content = eval_thunk(e2.thunk)
    elif isinstance(e, ReturnResponse):
      response.content = eval_thunk(e.thunk)
    elif isinstance(e, AssertionError):
      reraise(e.__class__, e, sys.exc_info()[-1])
    else :
      response.exception = e
      try:
        if self.debug:
          traceback_string = u_("env: %s") % repr(self.req.env)
          traceback_string += u_("\n") + u_(traceback.format_exc(), encoding=response.charset, errors='ignore')
          response.internal_error(u_("\n").join(["<pre>", traceback_string, "</pre>"]))
        elif self.error_handlers.get(500, None):
          response.internal_error(self.error_handlers[500]())
        else:
          response.internal_error("500 Internal Server Error")
      except ReturnResponse as e2:
        response.content = eval_thunk(e2.thunk)

  def convert_content(self, content):
    charset = self.res.charset
    if hasattr(content, 'read'):
      if 'wsgi.file_wrapper' in self.req._env:
        return self.req._env['wsgi.file_wrapper'](content)
      else:
        return iter(lambda: content.read(8192), b'')
    if isinstance(content, str):
      bytes = content.encode(charset)
      return [bytes]
    else:
      return [content]

  def convert_response(self, response):
    if self.req.method == "head":
      return []
    content = self.convert_content(response.content or b"")
    if response.get_header("Content-Length") is None:
      response.set_header("Content-Length", sum(len(v) for v in content))
    return content

  def _send_back_response(self, response):
    response.iterable_content = self.convert_response(response)
    self.run_hook("before_start_response")
    response.start_response()
    return response.iterable_content

  def stop(self):
    """Tells the run_xxx() loop to stop and waits until it does.
    """

    import signal
    os.kill(os.getpid(), signal.SIGINT)

  def serve_forever(self, **kw):
    """Handles requests until shutdown."""
    import argparse
    parser = argparse.ArgumentParser()
    servers = [name.replace("run_", "") 
      for name in dir(self) 
        if name.startswith("run_") and name not in ("run_cgi", "run_hook")]
    parser.add_argument('--server', choices=servers,
                        default="simple",
                        help='server type(default: %(default)s)')
    parser.add_argument('--port', default="7000", type=int,
                        help='port number(default: %(default)s)')
    parser.add_argument('params', nargs='*',
                        help='parameters for the server.')
    cmd_args = parser.parse_args()
    if cmd_args.params:
      kw["params"] = cmd_args.params
    getattr(self, "run_{}".format(cmd_args.server))(host="0.0.0.0", port=cmd_args.port, **kw)

  def run(self, server_func, host="127.0.0.1", port=8000, middlewares = [], **kw):
    """Runs this application as a server.
        ``self.debug`` will enable an autoreload support.

    :Parameters:
        server_func
            Function accepts four parameters : WSGI callable, host, port, ``**kw``
        host
            Host address
        port
            Server port
        middlewares
            List of WSGI middlewares
    """
    server_name = server_func.__name__.replace("_func","")
    if self.debug:
      if server_name in ("gevent", "fapws"):
        self.logger.warning("An auto-reloading does not work with this server.")
      else:
        server_func = self._run_with_autoreload(server_func)
    if not hasattr(self, "server_started"):
      self.server_started = True
      if self.debug:
        self.logger.info("%s server starting up... (%s:%d)"%(server_name.capitalize(), host, port))
      try:
        server_func(reduce(lambda r,v: v(r), middlewares, self), host, port, **kw)
      except KeyboardInterrupt:
        if self.debug:
          self.logger.info("Server shutting down...")
      delattr(self, "server_started")

  def _run_with_autoreload(self, run_server_func):
    def f(app, host, port, **kw):
      import imp

      mtimes = {}
      def update_mtime(file):
        try:
          new_mtime = os.stat(file).st_mtime
        except:
          return True
        if file in mtimes and new_mtime > mtimes[file]:
          return True
        mtimes[file] = new_mtime

      main_dir = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
      main = re.sub("\.pyc$", "\.py", getattr(sys.modules['__main__'], "__file__", ""))
      if main:
        update_mtime(main)
      for mod in iter_keys(sys.modules):
        if imp.is_builtin(mod) != 0 or not sys.modules[mod] or \
            mod == __name__ or not hasattr(sys.modules[mod], "__file__") or \
            not sys.modules[mod].__file__.startswith(main_dir): 
          continue
        update_mtime(sys.modules[mod].__file__)

      def run():
        while hasattr(app, "server_started"):
          for file in mtimes:
            if update_mtime(file):
              app.stop()
              # waiting for completion of shutdown...
              while hasattr(app, "server_started"): time.sleep(0.1)
              args = [sys.executable] + sys.argv
              if sys.platform == "win32":
                args = ['"%s"' % arg for arg in args]
              for trial in range(10):
                try:
                  os.execv(sys.executable, args)
                  return
                except OSError as e:
                  if e.errno != 45:
                    raise
                  time.sleep(0.1)
              else:
                raise
      threading.Thread(target=run).start()
      run_server_func(app, host, port, **kw)
    return f

  def run_cgi(self, middlewares = []):
    """Runs this application as a CGI handler."""
    wsgi_app = reduce(lambda r,v: v(r), middlewares, self)
    try:
      from google.appengine.ext.webapp.util import run_wsgi_app
      return run_wsgi_app(wsgi_app)
    except ImportError:
      from wsgiref.handlers import CGIHandler
      os.environ['PATH_INFO'] = os.environ['REQUEST_URI'].split("?")[0]
      if not os.environ["PATH_INFO"].startswith("/"):
        os.environ['PATH_INFO'] = "/"+ os.environ['PATH_INFO']
      return CGIHandler().run(wsgi_app)


  def run_simple(self, *args, **kw):
    """Runs Python-builtin WSGIServer hosting this application.

    Accepts same parameters as the ``run`` method.
    """
    from wsgiref import simple_server
    try:
      from SocketServer import ThreadingMixIn
    except:
      from socketserver import ThreadingMixIn
    class ThreadingWsgiServer(ThreadingMixIn, simple_server.WSGIServer): pass
    def simple_func(app, host, port):
      simple_server.make_server(host, port, app, ThreadingWsgiServer).serve_forever()
    self.run(simple_func, *args, **kw)

  def run_fapws(self, *args, **kw):
    """Runs fapws server hosting this application.
    **An auto-reloading does not work with run_fapws.**
    
    Accepts same parameters as the ``run`` method.
    """
    import fapws._evwsgi as evwsgi
    from fapws import base
    def fapws_func(app, host, port):
      port = n_(port)
      evwsgi.start(host, port)
      evwsgi.set_base_module(base)
      evwsgi.wsgi_cb(("", app))
      evwsgi.run()
    self.run(fapws_func, *args, **kw)

  def run_gevent(self, *args, **kw):
    """Runs gevent server hosting this application. 
    See "Asynchronous applications" for further documentations.
    **An auto-reloading does not work with run_gevent.**
    
    Accepts same parameters as the ``run`` method.

    :Additional parameters:
        websocket
            acts as a web socket server. (requires gevent-websocket, default: False)
    """
    from gevent import pywsgi
    def gevent_func(app, host, port, websocket = False, **kw):
      setattr(app.logger, "write", lambda v : app.logger.info(v.strip()))
      if websocket:
        from geventwebsocket.handler import WebSocketHandler
        pywsgi.WSGIServer((host, port), app, log=app.logger, handler_class=WebSocketHandler, **kw).serve_forever()
      else:
        pywsgi.WSGIServer((host, port), app, log=app.logger, **kw).serve_forever()
    self.run(gevent_func, *args, **kw)

  def run_gunicorn(self, *args, **kw):
    """Runs gunicorn server hosting this application. 
    **An auto-reloading does not work with run_gunicorn.**
    This method use a configuration file if there exists a file with the name ``gunicorn_conf.py``.
    This method accepts same parameters as the ``gunicorn`` command. See ``gunicorn -h``.

    Example::

        python index.py --server gunicorn --port 8000 -- -p index.pid -D
    """
    from subprocess import check_output
    def gunicorn_func(app, host, port, params=None):
      callee_module = sys.modules["__main__"]
      callee_path = os.path.abspath(callee_module.__file__)
      module_dir, file = os.path.split(callee_path)

      gunicorn_args = ["gunicorn", "-b", "%s:%d"%(host, int(port))]
      if params:
        gunicorn_args.extend(params)
      gunicorn_conf = os.path.join(module_dir, "gunicorn_conf.py")
      if os.path.exists(gunicorn_conf):
        gunicorn_args.extend(["-c", gunicorn_conf])

      os.chdir(module_dir)
      module_name, ext = os.path.splitext(file)
      app_name = ""
      for name in dir(callee_module):
        if getattr(callee_module, name) is app:
          app_name = name
          break
      gunicorn_args.append("{}:{}".format(module_name, app_name))
      gunicorn_path = os.path.abspath(check_output(["which", "gunicorn"])).strip()
      os.execv(gunicorn_path, gunicorn_args)
    self.run(gunicorn_func, *args, **kw)
    
#}}}

class AcceptanceValue(PropertyCachable): # {{{
  """'Accept-\*' header value.

  :Attributes:
      main_type     
          Main type.
      sub_type
          Sub type.
  """
  def __init__(self, main_type, sub_type, params):
    self.main_type = main_type
    self.sub_type = sub_type
    self.params = params

  @cached_property
  def q(self):
    """The type quality factor associated with this type."""
    q = self.params.get("q", None)
    if q is not None:
      return float(q)
    return 1.0

  def accepts_any_main_type(self):
    return (not self.main_type) or self.main_type == "*"

  def accepts_any_sub_type(self):
    return (not self.sub_type) or self.sub_type == "*"

  def __lt__(self, other):
    return self.__cmp__(other) < 0

  def __cmp__(self, other):
    if self.q > other.q: return -1
    if self.q < other.q: return 1
    if self.main_type != "*" and other.main_type == "*": return -1
    if self.main_type == "*" and other.main_type != "*": return 1
    if self.sub_type != "*" and other.sub_type == "*": return -1
    if self.sub_type == "*" and other.sub_type != "*": return 1
    if len(self.params) > len(other.params): return -1
    if len(self.params) < len(other.params): return 1
    return 0

  def __repr__(self):
    buffer = [self.main_type]
    if self.sub_type:
      buffer.append("/")
      buffer.append(self.sub_type)
    for key, value in iter_items(self.params):
      buffer.append(";")
      buffer.append(key)
      buffer.append("=")
      buffer.append(value)
    return "<%s %s>"%(self.__class__.__name__, "".join(buffer))
# }}}

class Accept(PropertyCachable): # {{{
  """Handles "Accept-\*" headers.(See RFC2616 Section 14.1 - 14.4)

  :Attributes:
      text
          Original header text.
  """
  TYPE_PATTERN = re.compile("\s*(?P<maintype>[^\s;,\n\/]+)(\/(?P<subtype>[^\s;,\n]+))?\s*(?P<param>(;[^,]+)*)")
  PARAM_PATTERN = re.compile("\s*(?P<paramname>[^\s;,\n]+)=(?P<paramvalue>[\d\.]+)*")
  def __init__(self, text):
    self.text = text

  def parse_text(self):
    values = []
    matches = self.TYPE_PATTERN.finditer(self.text)
    if matches:
      for match in matches:
        d = match.groupdict()
        if d["param"]:
          params = self.PARAM_PATTERN.findall(match.groupdict()["param"])
        else:
          params = []
        values.append(AcceptanceValue(d["maintype"], d["subtype"], dict(params)))
    values.sort()
    return values

  @cached_property
  def values(self):
    """List of AcceptanceValue objects."""
    return self.parse_text()

  def accepts(self, type, sub_type="*", params = None):
    """Returns the best matched AcceptanceValue object if the given type is acceptable for the response, otherwise None."""
    for v in self.values:
      if v.q == 0: return None

      if v.accepts_any_main_type() or type == "*" or v.main_type == type:
        if v.accepts_any_sub_type() or sub_type == "*" or v.sub_type == sub_type:
          if params:
            if all(v.params.get(pk, None) == pv for pk,pv in iter_items(params)):
              return v
          else:
            return v
    return None

class AcceptCharset(Accept):
  def parse_text(self):
    values = Accept.parse_text(self)
    if not values:
      return [AcceptanceValue("iso-8859-1", "", {"q":"1"})]
    return values

class AcceptLanguage(Accept):
  TYPE_PATTERN = re.compile("\s*(?P<maintype>[^\s;,\n\\-]+)(\-(?P<subtype>[^\s;,\n]+))?\s*(?P<param>(;[^,]+)*)")
  PARAM_PATTERN = re.compile("\s*(?P<paramname>[^\s;,\n]+)=(?P<paramvalue>[\d\.]+)*")

class AcceptEncoding(Accept):
  def parse_text(self):
    values = Accept.parse_text(self)
    if not values:
      return [AcceptanceValue("identity", "", {"q":"1"})]
    return values
# }}}

class Request(PropertyCachable): # {{{
  """Request.

  :Attributes:
      params     
          List of parameters as part of the requested URL
      action     
          Requested rays.Action object.
  """
  PARAM_NAME = re.compile("(\w+)\[(\w*)\]")
  def __init__(self, env):
    if env.get('HTTPS', '').lower() in ['on', 'true', '1'] or env.get("HTTP_X_FORWARDED_PROTO") == "https":
      env["wsgi.url_scheme"] = 'https'
    self._env = env
    self._path = "/"+env.get("PATH_INFO", env.get('REQUEST_URI', '').split("?")[0]).lstrip("/")
    self.params = []
    self.action = None

  @cached_property
  def input(self):
    """Returns a dictionary object with the GET and POST parameters."""
    input = {}
    def parse_input(k, value, is_list = False):
      m = self.PARAM_NAME.match(k)
      if m:
        name = m.group(1)
        key = m.group(2)
        if key:
          if name not in input:
            input[name] = {}
          d = input[name]
        else:
          d = input
          key = name
      else:
        d = input
        key = k
      if is_list or isinstance(d.get(key, None), list):
        if key not in d:
          d[key] = []
        d[key].append(value)
      else:
        d[key] = value

    if self.env.get('CONTENT_TYPE', '').lower().startswith('multipart/'):
      fp = self.env['wsgi.input']
    else:
      fp = BytesIO(self.env['wsgi.input'].read(self.content_length))
    storage = cgi.FieldStorage(fp=fp, environ=self.env, keep_blank_values=1)

    def _decode(v):
      if v.filename:
        return v
      v = v.value
      if isinstance(v, string_types):
        v = guess_decode(v)
      return v

    for k in storage:
      value = storage[k]
      if isinstance(value, list):
        [parse_input(k,_decode(v), True) for v in value]
      else:
        parse_input(k, _decode(value), False)

    for k,v in urllib.parse.parse_qsl(self.env.get('QUERY_STRING',"")):
      if isinstance(v, string_types):
        v = unquote_guess_decode(v)
      parse_input(k,v,False)

    return input

  env = property(lambda s:s._env, None, None, """Returns a dictionary object with the environment variables.""")
  path = property(lambda s:s._path, None, None, """Returns a path, such as /show/1  """)

  def get_header(self, name, default=None):
    """ Returns the value for the named header."""
    if not name.startswith("HTTP_"):
      name = name.replace('-', '_').upper()
      if not name.upper().startswith("CONTENT"):
        name = "HTTP_%s"%name
    return self.env.get(name, default)

  @cached_property
  def accept(self):
    """Returns an Accept object associated with the 'Accept' header."""
    return Accept(self.env.get("HTTP_ACCEPT", ""))

  @cached_property
  def accept_charset(self):
    """Returns an Accept object associated with the 'Accept-Charset' header."""
    return AcceptCharset(self.env.get("HTTP_ACCEPT_CHARSET", "*"))

  @cached_property
  def accept_language(self):
    """Returns an Accept object associated with the 'Accept-Charset' header."""
    return AcceptLanguage(self.env.get("HTTP_ACCEPT_LANGUAGE", "*"))

  @cached_property
  def accept_encoding(self):
    """Returns an Accept object associated with the 'Accept-Encoding' header."""
    return AcceptEncoding(self.env.get("HTTP_ACCEPT_ENCODING", "*"))

  @cached_property
  def cookies(self):
    """Returns a dictionary object with the cookies."""
    cookie = http.cookies.SimpleCookie()
    cookie.load(self.env.get('HTTP_COOKIE', ''))
    d = {}
    for k in cookie:
      d[k] = unquote_guess_decode(cookie[k].value)
    return d

  @cached_property
  def websocket(self):
    """Returns a websocket object."""
    return self.env.get("wsgi.websocket", None)

  @cached_property
  def is_xml_http_request(self):
    """ Returns true if the 'X-Requested-With' header contains 'XMLHttpRequest'"""
    return re.match("XMLHttpRequest", self.env.get("HTTP_X_REQUESTED_WITH", ""), re.I)

  @cached_property
  def http_version(self):
    """Returns a http version, such as 1.0(float)"""
    try:
      return float(self.env["SERVER_PROTOCOL"].replace("HTTP/", ""))
    except:
      return 1.0

  @cached_property
  def method(self):
    """Returns the HTTP REQUEST_METHOD as a lowercase string."""
    method = self.env["REQUEST_METHOD"].lower()
    if method == "post":
      return self.input.get("_method", method).lower()
    return method

  @cached_property
  def ua(self):
    """Returns the HTT_USER_AGENT"""
    return self.env.get("HTTP_USER_AGENT", "")

  @cached_property
  def content_length(self):
    """Returns the content length of the request as an integer."""
    return int(self.env.get('CONTENT_LENGTH', 0) or 0)

  @cached_property
  def is_ssl(self): 
    """Returns whether the request is under SSL."""
    return self.env["wsgi.url_scheme"] == 'https'

  @cached_property
  def format(self):
    """Returns the mime type for the request.

    The mime type is driven by the requested path extension.
    """
    return mimetypes.guess_type(self.path.split("/")[-1])[0] or "text/html"

  @cached_property
  def host_with_port(self):
    """Returns a string such as "example.com:8080"."""
    if self.env.get("HTTP_X_FORWARDED_HOST", None):
      return re.split(r",\s?",self.env["HTTP_X_FORWARDED_HOST"])[-1]
    return (self.env["HTTP_HOST"] or self.env["SERVER_NAME"] or self.env["SERVER_ADDR"])+":"+self.env["SERVER_PORT"]

  @cached_property
  def host(self): 
    """Returns the host."""
    return re.sub(r":\d+$", "", self.host_with_port)

  @cached_property
  def port(self): 
    """Returns the port as an integer."""
    return int(re.search(r":(\d+)$", self.host_with_port).group(1) or \
                                 self.is_ssl and 443 or 80)

  @cached_property
  def referer(self): 
    """Returns the referer."""
    return self.env.get("HTTP_REFERER", "")

  @cached_property
  def remote_addr(self):
    """Returns the remote address."""
    return self.env.get("REMOTE_ADDR", "")
    
# }}}

class Response(object): # {{{
  """Response.

  :Attributes:
      status_code
          HTTP status code
      charset
          Charcter set name for the response, such as "UTF-8"
      content
          Content for the response as an IO or string object 
      iterable_content
          Content for the response as an iterable object(list of bytes or an IO object)
      exception
          Exception that was raised while this request
      is_headers_written
          True if headers have already been sent, otherwise False
  """

  def __init__(self, start_response):
    self._headers = [("Accept-Ranges", "none"), ("Cache-Control", "no-cache")]
    self.content_type = 'text/html; charset=UTF-8'
    self.status_code = 200
    self.charset ='UTF-8'
    self.content = None
    self.iterable_content = None
    self.exception = None
    self.is_headers_written = False
    self._start_response = start_response

  content_type = property(lambda s: s.get_header('Content-type'),
                          lambda s,v: s.set_header('Content-type', v), None,
                          """Content-type for the response""")
  headers = property(lambda s: s._headers, 
                     None, None,
                    """List of tuples, such as [("Content-Type", "text/html")] """)
  status = property(lambda s: "%d %s"%(s.status_code, s.CODE_MAP[s.status_code]), 
                    None, None, 
                    """Status string for the response, such as "200 OK" """)

  def start_response(self):
    """Sends HTTP headers to the client."""
    if not self.is_headers_written:
      self._start_response(self.status, self.headers)
      self.is_headers_written = True

  def get_header(self, name):
    """ Returns the value for the named header.

    Returns a list if exists multiple headers of the same ``name``, otherwise a string.
    """
    result = [v for k,v in self._headers if k == name]
    if not result:
      return None
    return (len(result) > 1 and result or result[0])

  def set_header(self, name, value, unique=True):
    """ Adds the header ``name``: ``value`` for the response.

    if ``unique`` is True, ``name`` header will be overwritten by this value.
    """
    if unique:
      self.del_header(name)
    self._headers.append((name, n_(value)))

  def del_header(self, name):
    """Deletes the ``name`` headers."""
    self._headers = [(k,v) for k,v in self._headers if k != name]

  def set_cookie(self, name, value, expires="", domain=None, secure=False, path="/", **kargs):
    """Sets a cookie.

    :Parameters:
        expires
            Floating point number expressed in seconds since now
    """
    kargs["path"] = path
    if isinstance(expires, string_types):
      kargs["expires"] = ""
    else:
      if expires < 0: 
        expires = -1000000 
      kargs["expires"] = to_http_date_string(time.gmtime(time.time() + expires))
    if domain:
      kargs['domain'] = domain
    if secure:
      kargs['secure'] = secure
    cookie = http.cookies.SimpleCookie()
    cookie[name] = urllib.parse.quote(guess_decode(value).encode(self.charset))
    for key, val in iter_items(kargs):
      cookie[name][key] = val
    self.set_header('Set-Cookie', list(iter_items(cookie))[0][1].OutputString(), False)

  def _def_error(code):
    def _(self, v = None):
      self.status_code = code
      raise Abort(v, self.status)
    return _

  def _def_redirect(code):
    def _(self, url):
      self.status_code = code
      self.set_header("Location", url)
      return_response("")
    return _

  CODE_MAP = {
    200 : "OK",
    301 : "Moved Permanently",
    302 : "Found",
    303 : "See Other",
    304 : "Not Modified",
    307 : "Temporary Redirect",
    400 : "Bad Request",
    403 : "Forbidden",
    404 : "Not Found",
    405 : "Method Not Allowed",
    500 : "Internal Server Error"
  }

  moved_permanently  = _def_redirect(301)
  found              = _def_redirect(302)
  seeother           = _def_redirect(303)
  def not_modified(self):
    self.status_code = 304
    _headers = []
    for (k,v) in self._headers:
      if not k.startswith("X-"):
        continue
      _headers.append((k,v))
    self._headers = _headers
    return_response([])

  temporary_redirect = _def_redirect(307)
  redirect           = seeother

  badrequest         = _def_error(400)
  forbidden          = _def_error(403)
  notfound           = _def_error(404)
  method_not_allowed = _def_error(405)
  internal_error     = _def_error(500)


  def send_file(self, filepath, guess_mimetype = True, mimetype = 'text/plain', last_modified= None):
    """ Sends file data to a browser immediately."""
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
      self.notfound()
    if not os.access(filepath, os.R_OK):
      self.forbidden()

    if guess_mimetype:
      guessed = mimetypes.guess_type(filepath)[0]
      if guessed:
        self.content_type = guessed
    if not self.content_type and mimetype:
      self.content_type = mimetype
  
    stats = os.stat(filepath)
    if not self.get_header('Content-Length'):
      self.set_header('Content-Length',stats.st_size)
    if not self.get_header('Last-Modified'):
      if not last_modified:
        mtime = time.gmtime(stats.st_mtime)
        last_modified = time.strftime("%a, %d %b %Y %H:%M:%S +0000", mtime)
      self.set_header('Last-Modified', last_modified)
    if not self.get_header("Etag"):
      hasher = sha1()
      stat = os.stat(filepath)
      hasher.update(b_(filepath))
      hasher.update(b_(stat.st_mtime))
      hasher.update(b_(stat.st_size))
      self.set_header('Etag', '"%s"' % hasher.hexdigest())
    return_response(open(filepath, 'rb'))

  def get_is_success(self):
    return 200 <= self.status_code < 400

  is_success = property(get_is_success, None, None, "Returns whether or not this response indicates a successful.")

  def get_is_abort(self):
    return isinstance(self.exception, Abort)

  is_abort = property(get_is_abort, None, None, "Returns whether or not this response indicates a unsuccessful.")

  def get_is_error(self):
    return (not self.is_success) and (not self.is_abort)

  is_error = property(get_is_error, None, None, "Returns whether or not this response indicates a internal error.")

    
# }}}

# Embpy {{{
class EmbpyString(str): pass
class Embpy(object):
  BLOCK_START_PAT = re.compile(r".*:\s*$")
  VERSION_SUFFIX = u_("").join(map(str, list(sys.version_info)))

  def _lazy(lock):
    def deco(f):
      v = [None]
      def _(*args):
        with lock:
          if not v[0]:
            v[0] = f(*args)
        return v[0]
      return _
    return deco

  @staticmethod
  @_lazy(threading.Lock())
  def scanner():
    from re import Scanner
    action = lambda token_type: lambda scanner, s: [token_type, s]
    return Scanner([
      (r""""(((?<=\\)")|[^"])*((?<!\\)")""", action("string")),
      (r"""'(((?<=\\)')|[^'])*((?<!\\)')""", action("string")),
      (r"""\s*(else|elif|except|finally)(:|[ \(]("([^\\"]|\\.)*"|'([^\\']|\\.)*'|[^:"'])*[^{]:)""", action("block_keyword")),
      (r"""\{:""", action("indent_start")),
      (r""":\}|([\s]end(?=\s))""", action("indent_end")),
      (r"""^\s*end\s*$""", action("indent_end")),
      (r""";""", action("newline")),
      (r"""(\s(else|elif|except|finally|end))""", action("others")),
      (r"""(?:(?!((\{:|:\}|[\s]end)|(\s(else|elif|except|finally))|[;]))[^"'])*""", action("others")),
    ], re.M|re.S)

  @staticmethod
  @_lazy(threading.Lock())
  def splitter():
    return re.compile(r"""((?P<print_code><%=(?P<raw_mode>(r )?))|((?P<s_space>^[ \t]*)(?P<trim_start><%\-))|(<%(?!%)(?:\-?)))(?P<code_body>("([^\\"]|\\.)*"|'([^\\']|\\.)*'|(?:(?!(%>)).))*)((?P<trim_end>\-%>[\n]?)|(?P<end_tag>[^%]%>))""", re.M|re.S)


  def __init__(self, template, cache_path = "", template_globals = None, filter=None, encoding="utf8"):
    self.code = ["__buffer= []\n__buffer_append = __buffer.append\n"]
    self.src  = ""
    self.indent = 0
    self.template = getattr(template, "read", lambda: template)()
    self.file_path = getattr(template, "name", None)
    self.encoding = encoding
    if isinstance(self.template, bytes):
      self.template = self.template.decode(self.encoding)
    self.cache_path = cache_path and cache_path+"_"+self.VERSION_SUFFIX or ""
    self.template_globals = template_globals or {}
    self.filter = filter
    if filter:
      def _(s):
        if not isinstance(s, EmbpyString) :
          return EmbpyString(filter(u_(s)))
        else:
          return s
      self.template_globals["__filter"] = _

  def set_template_globals(self, dct = None):
    self._template_globals = dct or {}
    self._template_globals.update({"u_":u_,"b_":b_,"n_":n_})

  def get_template_globals(self):
    return self._template_globals

  template_globals = property(get_template_globals, set_template_globals)

  def is_cached(self):
     return self.file_path and self.cache_path and \
     os.path.exists(self.file_path) and os.path.exists(self.cache_path) and \
     os.path.getmtime(self.file_path) < os.path.getmtime(self.cache_path)

  def compile(self):
    if isinstance(self.code, list):
      if self.is_cached(): 
        self.code = marshal.load(open(self.cache_path, "rb"))
      else:
        s = self.template
        search = self.splitter().search
        scan = self.scanner().scan
        m = True
        pos = 0
        while m:
          m = search(s, pos=pos)
          if m:
            text = s[pos:m.start()]
          else:
            text = s[pos:]
          self.append(self.escape_string(text))
          if not m:
            break

          d = m.groupdict()
          pos = m.end()
          code_body = [d.get("code_body") or ""]

          if not d.get("trim_end"):
            v = d.get("end_tag")[0]
            if v != "-":
              code_body.append(v)

          if d.get("print_code"):
            self.do_indent()
            if self.filter and not d["raw_mode"]:
              self.code.append(u_("__buffer_append(__filter("))
            else:
              self.code.append(u_("__buffer_append(u_("))

          code_body = u_("").join(code_body)
          if not code_body.strip():
            # <% %>: indent end
            self.indent_end("")
          else:
            self.do_indent()
            for token_type, value in scan(code_body)[0]:
              getattr(self, token_type)(value)

          if d.get("print_code"):
              self.code.append(u_("))"))

        self.do_indent()
        self.src = u_("").join(self.code)
        try:
          self.code = compile(self.src, "<string>", "exec")
        except SyntaxError as e:
          e.text = u_("\n").join(self.src.splitlines()[0:e.lineno])
          e.args = ('invalid syntax', ('<string>', e.lineno, e.offset, e.text))
          reraise(e.__class__, e, sys.exc_info()[-1])
        if self.file_path and self.cache_path:
          marshal.dump(self.code, open(self.cache_path, "wb"))
    return self.code

  def render(self, vars = None):
    vars = vars or {}
    vars.update(self.template_globals)
    try:
      exec_function(self.compile(), vars, vars)
    except Exception as e:
      if self.src and not isinstance(e, SyntaxError):
        m = re.match(".*line (\d+).*", traceback.format_exc().splitlines()[-2])
        if m:
          line =  int(m.group(1))
          buf = [e.args[0]]
          start = max(line-5, 0)
          for i, v in enumerate(self.src.splitlines()[start:line+5]):
            buf.append(u_("%04d : %s")%(start+i+1, v))
          e.message = u_("\n").join(buf)
          e.args = [e.message]
      reraise(e.__class__, e, sys.exc_info()[-1])
    return EmbpyString(u_("").join(vars["__buffer"]))

  def append(self, s):
    if not s:
      return
    self.do_indent()
    self.code.append(u_("__buffer_append(u_(\"\"\"%s\"\"\"))")%s)

  def do_indent(self, *a):
    self.code.append(u_("\n%s")%(u_("  ")*self.indent))

  def escape_string(self, s):
    return s.replace('"', '\\"').replace("<%%","<%").replace("%%>","%>")

  def others(self, s):
    for line in s.splitlines():
      line_striped = line.lstrip()
      if self.BLOCK_START_PAT.match(line_striped):
        self.code.append(line_striped)
        self.indent += 1
      else:
        self.code.append(line_striped)
      self.do_indent()
    self.code.pop()

  def string(self, s):  self.code.append(s)
  def newline(self, s): self.do_indent()

  def indent_start(self, s):
    self.indent += 1
    self.code.append(u_(":"))
    self.do_indent()

  def indent_end(self, s):
    self.indent -= 1
    self.do_indent()

  def block_keyword(self, s):
    self.indent -= 1
    self.do_indent()
    self.code.append(s.lstrip())
    self.indent += 1
# }}}

class Helper(object): # {{{
  """ """
  buffer_search_limit = 10

  def _buffer_frame_locals(self):
    for i in range(2, self.buffer_search_limit):
      f = sys._getframe(i).f_locals
      if "__buffer" in f:
        return f
  buffer_frame_locals = property(_buffer_frame_locals)
  get_buffer_frame_locals = classmethod(_buffer_frame_locals)

  @contextlib.contextmanager
  def capture(self, name):
    """ Stores a block of markup in ``name``.

    example::

        <% with h.capture("header"): %>
          <script type="text/javascript>alert("hello!");</script>
          <% %>
        <%=r header %>

    """
    locals = self.buffer_frame_locals
    start_index = len(locals["__buffer"])
    yield 
    locals.update({name:EmbpyString(u_("").join(locals["__buffer"][start_index:]))})
    del locals["__buffer"][start_index:]

  def concat(self, value):
    """ Adds ``value`` to the output buffer. """
    self.buffer_frame_locals["__buffer_append"](value)

  def captured(self, value):
    return self.buffer_frame_locals[value]

  @classmethod
  def htmlquote(*a): 
    """ Escapes HTML tag characters."""
    text = a[-1]
    return escape_html(text)
# }}}

class Renderer(object): # {{{
  """ """
  extensions = [".html", ".xml", ".js", ".epy", ".pyhtml"]
  def __init__(self, template_dir, cache_dir, template_globals = None, filter = None, encoding = "utf8"):
    self.template_dir = template_dir
    self.cache_dir    = cache_dir
    self.template_globals = template_globals or {}
    self.filter = filter
    self.encoding = encoding
    self.embpy_cache = {}
    self.lock = threading.Lock()

  def set_template_globals(self, dct):
    self._template_globals = {
      "h": Helper()
    }
    self._template_globals.update(dct)
    self._template_globals["renderer"] = self

  def get_template_globals(self):
    return self._template_globals

  template_globals = property(get_template_globals, set_template_globals)

  def create_embpy(self, template, name = "", encoding=None):
    return Embpy(template,
                cache_path = self.cache_dir and os.path.join(self.cache_dir, name) or None,
                template_globals = self.template_globals,
                filter = self.filter,
                encoding = encoding)

  def render_file(self, name, vars = None, encoding = None):
    """Renders the template file.
    
    ``Renderer.index(vars, encoding)`` is same as ``Renderer.render_file("index", vars, encoding).``
    """
    template = os.path.join(self.template_dir, name)
    if not "." in name:
      for i in self.extensions:
        template_cand = template+i
        if os.path.exists(template_cand):
          template = template_cand
          name = name+i
    with self.lock:
      embpy = self.embpy_cache.get(template, None)
      if not embpy:
        embpy = self.create_embpy(open(template, "rb"), name, encoding=encoding or self.encoding)
        self.embpy_cache[template] = embpy
    return embpy.render(vars or {})
  render = render_file

  def __getattr__(self, name):
    if name.startswith("with_layout"):
      method = "render%s"%name[len("with_layout"):]
      locals = Helper.get_buffer_frame_locals()
      body = EmbpyString(u_("").join(locals["__buffer"]))
      locals["__buffer"][:] = []
      locals["body"] = body
      return lambda t, *a, **k: getattr(self, method)(t, locals, *a, **k)
    else:
      return lambda *a, **k: self.render_file(name, *a, **k)

  def render_string(self, template, vars = None):
    """Renders the template string."""
    return self.create_embpy(template).render(vars or {})
# }}}

# Extensions {{{
class Extension(object): # {{{
  """Base class for extensions.

  rays includes an API for extension writers to add their own features to the application.
  """

  def __init__(self, app, ext_name = None):
    self.app = app
    ext_name = ext_name or to_snake_case(self.__class__.__name__[:-9])
    if ext_name in self.app.ext:
      raise ValueError("Extension '%s' is already loaded."%ext_name)
    setattr(self.app.ext, ext_name, self)

  @classmethod
  def app_config(cls, app, dct):
    """Method called when the extension is configured by calling the ``Application.config`` method.
    """
    return cls(app, **dct)
# }}}

class ExtensionLoader(object): # {{{
  """ """

  def __init__(self, app, ext_module):
    self.app        = app
    self.ext_module = ext_module

  def load(self):
    """Loads all extensions found in the ``ext_module``.

    To turn an extension off, prefix it's module name with an underscore.
    """
    directory = os.path.dirname(self.ext_module.__file__)
    lst = os.listdir(directory)
    lst.sort()
    g = globals()
    for name in lst:
      if name[0] == "_":
        continue
      if os.path.isdir(os.path.join(directory, name)) and not os.path.exists(os.path.join(directory, name, "__init__.py")):
        continue
      
      if name[-3:] == ".py" or "." not in name:
        modname = name.replace(".py", "")
        __import__(self.ext_module.__name__+"."+modname)
        mod = getattr(self.ext_module, modname)
        for attr_name in dir(mod):
          val = getattr(mod, attr_name)
          if isinstance(val, type) and issubclass(val, Extension):
            g[val.__name__] = val
            self.app.run_hook("after_load_extension", [val.__name__, val])

# }}}

# Database Extension {{{
# DatabaseExtension {{{
class DatabaseExtension(Extension):
  """Database management extension.

  :Available configuration parameters:
      connection 
          str, sqlite3 database file name.
      transaction 
          str, transaction behavior.

              - ``commit_on_success`` : When a request starts, rays starts a transaction. If the response is produced without problems, rays commits transactions. Otherwise, rays rolls back transactions.
              - ``commit_auto`` 
              - ``programmatic`` 
  """

  def __init__(self, app, connection, transaction = "commit_on_success"):
    global sqlite3
    import sqlite3
    Extension.__init__(self, app)
    self.connection =  connection
    self.transaction = transaction

    self.app.add_hook("before_dispatch",
                      self.on_before_dispatch,
                      name = "DatabaseExtension", pos="first")

    self.app.add_hook("before_start_response",
                      self.on_before_start_response,
                      name = "DatabaseExtension", pos="last")
    self.app.define_tls_property("db", "rays.Database object")

  def create_new_session(self):
    """Returns a Database object with new connection.
    """
    db = None
    if self.connection:
      db = Database(self.connection)
      db.autocommit = self.transaction == "commit_auto"
      db.app = self.app
    return db

  def on_before_dispatch(self, *a):
    self.app.db = self.create_new_session()

  def on_before_start_response(self, *a):
    try:
      if self.transaction == "commit_on_success" and self.app.db.transaction_started:
        if self.app.res.is_success:
          self.app.db.commit()
        else:
          self.app.db.rollback()
    finally:
      self.app.db.close()
# }}}

class Model(HookableClass): # {{{
  """

  :Class hooks:
      before_create(obj)
          called before ``insert``
      after_create(obj)
          called after ``insert``
      before_save(obj)
          called before ``insert`` and ``update``
      after_save(obj)
          called after ``insert`` and ``update``
      before_delete(obj)
          called before ``delete``
      after_delete(obj)
          called after ``delete``
  """

  def class_init(cls):
    HookableClass.class_init(cls)

    cls.snake_case_name = to_snake_case(cls.__name__)
    if not getattr(cls, "table_name", None):
      cls.table_name = cls.snake_case_name

  @classmethod
  def reference_class(cls, name, f):
    class A(object):
      def __init__(self): self.cache = None
      def __get__(self, ins, klass):
        self.cache = self.cache or type(name, (eval_thunk(f),), {})
        return self.cache
    setattr(cls, name, A())

  def __init__(self, **kw):
    for k,v in iter_items(kw):
      setattr(self, k, v)

  def __repr__(self):
    return "<%s %s>"%(self.__class__.__name__, self.__dict__)
# }}}

class Database(object): # {{{
  """Simple wrapper for sqlite3

  Database tables must have a  column ``id INTERGER NOT NULL PRIMARY KEY AUTOINCREMENT``
  as a prerequisite for using this class.

  """
  RETRY_LIMIT = 30
  RETRY_WAIT_SEC  = 0.01
  def __init__(self, connection):
    self.connection_params = dict(database=connection, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    self._connection = None
    self._schema = collections.defaultdict(dict)
    self.transaction_started = False
    self.has_executed_query = False
    def factory(cursor, row):
      class _(sqlite3.Row):
        def __init__(self, cursor, row):
          super(_, self).__init__(cursor, row)
          self.keys = lambda : [col[0] for col in cursor.description]
          self.iterkeys = lambda : (col[0] for col in cursor.description)
      return _(cursor, row)
    self.connection.row_factory = factory
    self.app = None

  @property
  def connection(self):
    if not self._connection:
      self._connection = sqlite3.connect(**self.connection_params)
    return self._connection

  @property
  def schema(self):
    if len(self._schema) == 0:
      self.load_schema()
    return self._schema

  def _execute(self, obj, *args, **kw):
    if not self.has_executed_query:
      self.has_executed_query = True
      if hasattr(self, "app"):
        self.app.run_hook("after_connect_database", [self])

    if not self.transaction_started and not kw.pop("without_transaction", None):
      if not self.autocommit:
        self.begin()

    is_debug = hasattr(self, "app") and self.app and self.app.debug
    if is_debug:
      self.app.logger.debug(",".join(u_(a) for a in args) + ", "+ u_(kw))
    exception = None
    for i in range(self.RETRY_LIMIT):
      try:
        return obj.execute(*args, **kw)
      except sqlite3.OperationalError as e:
        exception = e
        if e.args[0] == "database is locked":
          if is_debug:
            self.app.logger.debug(threading.currentThread().getName()+": Database is locked. retrying.")
          time.sleep(self.RETRY_WAIT_SEC)
        else:
          break
    if exception:
      raise exception

  def close(self):
    """Closes this database connection."""
    self.connection.close()

  def execute(self, *args, **kw):
    """Executes an SQL statement.

    >>> db = app.ext.database.create_new_session()
    >>> db.execute("CREATE TABLE tests(name TEXT)")
    >>> db.execute("INSERT INTO tests (name) VALUES ('john')")
    >>> db.execute("SELECT * FROM tests WHERE name=?", "john")
    
    """
    return self._execute(self.connection, *args, **kw)

  def load_schema(self):
    cur = self.connection.cursor()
    cur.execute("SELECT * from sqlite_master;")
    for i, row in enumerate(cur):
      if row[0] == "table":
        d = self._schema[row[1]]
        d["table"] = row[4]
        d["colnames"] = [v.strip().split(" ")[0]
                          for v in row[4].split("(")[1].split(",")]
        d["index"] = []
      elif row[0] == "index":
        if "index" not in self._schema[row[2]]:
          self._schema[row[2]]["index"] = []
        self._schema[row[2]]["index"].append(row[1])
    cur.close()

  def set_autocommit(self, value):
    if value:
      self.connection.isolation_level = None
    else:
      self.connection.isolation_level = "DEFERRED"
  autocommit = property(lambda s: s.connection.isolation_level is None, set_autocommit, None,
                        """Sets whether autocommit mode is enabled.""")

  def __getattr__(self, key):
    if key.startswith("select_one"):
      def _(*args, **kw):
        result = list(getattr(self, key.replace("select_one","select"))(*args, **kw))
        return len(result) and result[0] or None
      return _
    return getattr(self.connection, key)
  
  @contextlib.contextmanager
  def transaction(self):
    """ Creates a new transaction.

    This method can be used as context managers for a ``with`` statement

    >>> db = app.ext.database.create_new_session()
    >>> with db.transaction():
    ...   raise Exception() # rollback


    """
    self.begin()
    try:
      yield
      self.commit()
    except Exception:
      self.rollback()
      raise

  def begin(self):
    """Begins a new transaction."""
    old_transaction_started = self.transaction_started
    self.transaction_started = True
    if not old_transaction_started:
      self.execute("BEGIN")

  def commit(self):
    """Commits the transaction."""
    old_transaction_started = self.transaction_started
    self.transaction_started = False
    if old_transaction_started: 
      if self.app.debug:
        self.app.logger.debug("COMMIT")
      self.connection.commit()

  def rollback(self): 
    """Roll backs the transaction."""
    old_transaction_started = self.transaction_started
    self.transaction_started = False
    if old_transaction_started:
      if self.app.debug:
        self.app.logger.debug("ROLLBACK")
      self.connection.rollback()

  def shell(self):
    """Starts a interactive database shell."""
    con = self.connection
    old_isolation_level = con.isolation_level
    con.isolation_level = None
    cur = con.cursor()
    buffer = u_("")
    print("Enter your SQL commands to execute in sqlite3.")
    print("Enter 'exit' to exit.")
    while True:
      line = input(">>")
      if line.strip() == "exit":
        break
      buffer += line
      if sqlite3.complete_statement(buffer):
        try:
          buffer = buffer.strip()
          cur.execute(buffer)
          if re.match("^\s*(select).*", buffer, re.I):
            result = [(name[0] for i, name in enumerate(cur.description))] + cur.fetchall()
          elif re.match("^s*(update|delete|insert).*", buffer, re.I):
            result = cur.rowcount
          else:
            result = cur.fetchall()
          if isinstance(result, (int, long)):
            result = "OK, %d %s affected."%(result, result > 1 and "rows" or "row")
          elif isinstance(result, (list, tuple)):
            result = "\n".join(["| %s |"%("\t| ".join(map(u, row))) for row in result])
          print(result)
        except sqlite3.Error as e:
          print("An error occured:", e.args[0])
        buffer = ""
    con.isolation_level = old_isolation_level

  def select(self, tables, select = "SELECT %(all)s FROM %(tables)s", cond="1", values=None):
    """Executes a select query and mapping it ``tables``.

    Example::
        >>> result = list(db.select([WebPage, WebSite], cond="WebPage.site_id=WebSite.id and WebPage.id=?",values=[1]))
        >>> print(result[0].web_page, result[0].web_site)
        >>> db.select([WebPage], cond="1 ORDER BY created_at DESC") # needs "1"
        >>> db.select_one([WebPage])
    """
    query = select + " WHERE "+ cond
    params = {}
    params["tables"] = ",".join("`%s` as `%s`"%(table.table_name, table.__name__) for table in tables)
    params["all"] = ",".join(",".join("`%s`.`%s` as `%s___%s`"%(table.__name__, name, table.__name__, name)
                                      for name in self.schema[table.table_name]["colnames"])
                                      for table in tables)
    table_index = dict((table.__name__, table) for table in tables)
    for v in  self.execute(query%params, values or []).fetchall():
      d = collections.defaultdict(dict)
      result = DefaultAttrDict({}, dict)
      for col_name in iter_keys(v):
        try:
          table_name, col = col_name.split("___")
          d[table_name][col] = v[col_name]
        except:
          d[tables[0].__name__][col_name] = v[col_name]
      for table_name in d:
        table_class = table_index[table_name]
        result[table_class.snake_case_name] = result[table_class] = table_class(**d[table_name])
      yield (len(tables) == 1 and result[list(iter_keys(result))[0]] or result)
  select_all = select

  def insert(self, obj):
    """Inserts ``obj`` to the database."""
    obj.run_hook("before_create", [obj])
    obj.run_hook("before_save", [obj])
    table_name = obj.__class__.table_name
    colnames = self.schema[table_name]["colnames"]
    names = ",".join("`%s`"%c for c in colnames)
    values = [getattr(obj,c,None) for c in colnames]
    bind = ",".join(["?"]*len(colnames))
    cur = self.connection.cursor()
    self._execute(cur, "INSERT INTO `%(table_name)s` (%(names)s) VALUES (%(bind)s);"%locals(), values)
    obj.id = cur.lastrowid
    obj.run_hook("after_create", [obj])
    obj.run_hook("after_save", [obj])

  def update(self, obj):
    """Updates the table with ``obj``."""
    obj.run_hook("before_save", [obj])
    table_name = obj.__class__.table_name
    colnames = self.schema[table_name]["colnames"]
    data = ",".join("`%s`=?"%c for c in colnames)
    values = [getattr(obj,c,None) for c in colnames] + [obj.id]
    result = self.execute("UPDATE `%(table_name)s` SET %(data)s WHERE `id`=?"%locals(), values).rowcount
    obj.run_hook("after_save", [obj])
    return result

  def save(self, obj):
    """Saves the ``obj``."""
    if getattr(obj, "id", None):
      self.update(obj)
    else:
      self.insert(obj)

  def delete(self, obj):
    """Deletes ``obj`` from the table."""
    obj.run_hook("before_delete", [obj])
    table_name = obj.__class__.table_name
    result = self.execute("DELETE FROM `%(table_name)s` WHERE `id`=?"%locals(), [obj.id]).rowcount
    obj.run_hook("after_delete", [obj])
    return result
# }}}
# }}}

# Session Extension {{{
class SessionExtension(Extension): # {{{
  """Session management extension.

  :Available configuration parameters:
       - store : str, default ``"File"``
       - expires: integer expressed in seconds since now, default ``60*60*24``
       - secret: str, **required**
       - cookie_name: str, default ``"session_id"``
       - cookie_domain:str 
       - cookie_secure: boolean
       - cookie_path: str
       - cookie_expires: integer expressed in seconds since now
  """
  def __init__(self, app, cookie_name="session_id", cookie_expires="", cookie_domain=None, 
                     cookie_secure=False, cookie_path="", store=None):
    import base64
    import hmac
    globals().update({"sha1":sha1, "pickle":pickle, "base64":base64, "hmac":hmac})

    Extension.__init__(self, app)
    self.cookie_name    = cookie_name
    self.cookie_domain  = cookie_domain
    self.cookie_secure  = cookie_secure
    self.cookie_path    = cookie_path
    self.cookie_expires = cookie_expires
    self.store          = store

    self.app.add_hook("before_action",
                      self.on_before_action,
                      name = "SessionExtension", 
                      pos="after_DatabaseExtension")

    self.app.add_hook("before_start_response",
                      self.on_before_start_response,
                      name = "SessionExtension",
                      pos="before_DatabaseExtension")
    self.app.define_tls_property("session", "rays.SessionStoreBase object")

  @classmethod
  def app_config(cls, app, dct):
    session_config = dict((k,v) for k,v in iter_items(dct) if k.startswith("cookie_"))
    store_config = dict((k,v) for k,v in iter_items(dct) if not k.startswith("cookie_"))
    store_type = store_config.pop("store", "File")
    if isinstance(store_type, string_types):
      store_class = eval("%sSessionStore"%store_type)
    else:
      store_class = store_type
    store_config["app"] = app
    session_config["store"] = store_class(**store_config)
    session_config["app"]   = app
    SessionExtension(**session_config)

  def __getattr__(self, name):
    """ Delegates attributes to the ``SessionStoreBase`` object."""
    return getattr(self.store, name)

  def on_before_action(self, *a):
    try:
      if not self.app.req.path.startswith(self.app.base+self.cookie_path):
        return

      tamper_proof_session_id = self.app.req.cookies.get(self.cookie_name, None)
      if not tamper_proof_session_id:
        self.app.session = self.store.new()
      else:
        self.app.session = self.store.load(tamper_proof_session_id)
    except SessionLoadError:
      self.app.session = self.store.new()

  def on_before_start_response(self, *a):
    if not self.app.res.is_success:
      return 
    if not self.app.req.path.startswith(self.app.base+self.cookie_path):
      return
    cookie_args = dict(domain = self.cookie_domain, expires = self.cookie_expires,
                       secure = self.cookie_secure, path = self.app.base+self.cookie_path)
    if self.app.session.killed:
      cookie_args["expires"] = -1
      self.app.res.set_cookie(self.cookie_name, "", **cookie_args)
      self.store.delete(self.app.session.session_id)
      self.app.session.session_id = None

    if len(self.app.session):
      if not self.app.session.session_id :
        session = self.store.create()
        session.update(self.app.session)
        self.app.session = session
      self.app.res.set_cookie(self.cookie_name, 
        self.store.encode(self.app.session.session_id, tamper_proof=True), **cookie_args)
      self.store.save(self.app.session)

class SessionLoadError(Exception): pass
#}}}

class Session(dict): # {{{
  """
  """
  def __init__(self, session_id):
    self.session_id = session_id
    self.killed = False

  def kill(self):
    """Kills the session."""
    self.killed = True
    self.clear()

  def __missing__(self, key):
    return None
#}}}

class SessionStoreBase(object): # {{{
  """ """

  def __init__(self, app, secret=None, expires=60*60*24):
    self.app     = app
    self.expires = expires
    self.secret  = secret
    if self.secret is None or not self.secret:
      raise ValueError("secret is required and must be a non empty string.")

  def generate_session_id(self):
    """Generates a session id."""
    while True:
      now = time.time()
      rand = os.urandom(16)
      session_id = sha1(b_("%s%s%s%s"%(rand, now, self.secret, getattr(os,"getpid", lambda : 1)()))).hexdigest()
      if not self.exists(session_id):
        return session_id

  def encode(self, obj, tamper_proof = False):
    """Returns a string representation of the ``obj``.

    If the ``tamper_proof`` is true, the string holds a HMAC signature of the random value.
    """
    string = base64.encodestring(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL))
    if tamper_proof:
      return "%s----%s"%(n_(string), n_(hmac.new(b_(self.secret), b_(string), sha1).hexdigest()))
    else:
      return b_(string)

  def decode(self, data, tamper_proof = False):
    """Returns a python representation of the ``data``.

    If the ``tamper_proof`` is true, validates the HMAC signature in the ``data``.
    If the ``data`` is tampered, returns None.
    """
    if tamper_proof:
      parts = data.split("----")
      main  = parts[0]
      digest = "----".join(parts[1:])
      if digest == n_(hmac.new(b_(self.secret), b_(main), sha1).hexdigest()):
        return self.decode(main, False)
      else:
        return None
    else:
      return pickle.loads(base64.decodestring(b_(data)))

  def exists(self, session_id): 
    """Returns True if ``session_id`` is exists."""
    raise NotImplementedError()

  def new(self):
    """Returns a new ``Session`` object with empty session id. """
    return Session(None)

  def create(self):
    """Creates and returns a new ``Session`` object with a new session id."""
    raise NotImplementedError()

  def save(self, session):
    """ Saves the ``session``."""
    raise NotImplementedError()

  def load(self, tamper_proof_session_id):
    """Loads a ``Session`` object. """
    raise NotImplementedError()

  def delete(self, session_id):
    """Deletes session data indicated by the ``session_id``."""
    raise NotImplementedError()

  def cleanup(self):
    """Deletes expired session data."""
    raise NotImplementedError()

  def count(self):
    """Returns the number of sessions"""
    raise NotImplementedError()
# }}}

class FileSessionStore(SessionStoreBase): # {{{
  """ Implements a file system based ``SessionStoreBase``."""

  def __init__(self, root_path, *a, **kw):
    super(FileSessionStore, self).__init__(*a, **kw)
    self.root_path = root_path
    self.lock = threading.Lock()
    if not os.path.exists(self.root_path):
      os.makedirs(self.root_path)

  def path(self, session_id):
    return os.path.join(self.root_path, session_id.replace("..",""))

  def exists(self, session_id):
    return os.path.exists(self.path(session_id))

  def create(self):
    with self.lock:
      session_id = self.generate_session_id()
      with open(self.path(session_id), "w") as io:
        io.write("")
    return Session(session_id)
  
  def save(self, session):
    with open(self.path(session.session_id), "wb") as io:
      io.write(self.encode(session))

  def load(self, tamper_proof_session_id):
    session_id = self.decode(tamper_proof_session_id, tamper_proof=True)
    if session_id is None:
      raise SessionLoadError()

    path = self.path(session_id)
    if os.path.exists(path):
      if (time.time() - os.stat(path).st_atime) > self.expires:
        self.delete(session_id)
      else:
        session = Session(session_id)
        session.update(self.decode(open(path, "rb").read()))
        return session
    raise SessionLoadError()

  def delete(self, session_id):
    os.remove(self.path(session_id))

  def cleanup(self):
    now = time.time()
    for f in (f for f in os.listdir(self.root_path) if not f.startswith(".")):
      path = self.path(f)
      if now - os.stat(path).st_atime > self.expires:
        os.remove(path)

  def count(self):
    return len([i for i in os.listdir(self.root_path) if not i.startswith(".")])
# }}}

class DatabaseSessionStore(SessionStoreBase): # {{{
  """ Implements a database based ``SessionStoreBase``.
  """

  SCHEMA="""
    CREATE TABLE rays_sessions (
      id INTEGER PRIMARY KEY NOT NULL,
      session_id TEXT NOT NULL,
      data       TEXT NOT NULL,
      created_at TIMESTAMP NOT NULL,
      updated_at TIMESTAMP NOT NULL
    );
  """
  INDEX="""
    CREATE INDEX rays_sessions_session_id_idx on rays_sessions(session_id);
  """

  class SessionData(Model):
    table_name="rays_sessions"

    def class_init(cls):
      Model.class_init(cls)

      @cls.hook("before_create")
      def before_create(self):
        self.created_at = datetime.now()

      @cls.hook("before_save")
      def before_save(self):
        self.updated_at = datetime.now()

  def __init__(self, *a, **kw):
    super(DatabaseSessionStore, self).__init__(*a, **kw)
    self.lock = threading.Lock()

  def get_session_data(self, session_id):
    return self.app.db.select_one([self.SessionData], cond="session_id=?", values=[session_id])

  def exists(self, session_id):
    return self.get_session_data(session_id)

  def create(self):
    with self.lock:
      session_id   = self.generate_session_id()
      session_data = self.SessionData(session_id = session_id, data="")
      self.app.db.insert(session_data)
    return Session(session_id)
  
  def save(self, session):
    session_data = self.get_session_data(session.session_id)
    session_data.data = self.encode(session)
    self.app.db.update(session_data)

  def load(self, tamper_proof_session_id):
    session_id = self.decode(tamper_proof_session_id, tamper_proof=True)
    if session_id is None:
      raise SessionLoadError()

    session_data = self.get_session_data(session_id)
    if session_data:
      if (time.time() - time.mktime(datetime.timetuple(session_data.updated_at))) > self.expires:
        self.delete(session_id)
      else:
        session = Session(session_id)
        session.update(self.decode(session_data.data))
        return session
    raise SessionLoadError()

  def delete(self, session_id):
    self.app.db.delete(self.get_session_data(session_id))

  def cleanup(self):
    limit = datetime.now() - timedelta(seconds=self.expires)
    self.app.db.execute("DELETE FROM %s WHERE updated_at < ?"%self.SessionData.table_name, [limit])

  def count(self):
    return len(list(self.app.db.select([self.SessionData])))
# }}}
# }}} 

class StaticFileExtension(Extension): # {{{
  """Static file serving extension.

  :Available configuration parameters:
       - url : str, such as "statics/"
       - path : str, such as "/home/www/app/statics"
       - cache : Integer, a cache expiry in secounds. default: 86400*365(a year)
                 Does not cache if the ``chache`` is negative.
  """
  def __init__(self, app, url, path, cache = 86400*365):
    Extension.__init__(self, app)
    self.url  = url
    self.path = path
    self.cache = cache
    self.hashes = {}
    self.lock = threading.Lock()
    self.app.add_hook("before_initialize",
                      self.on_before_initialize,
                      name = "StaticFileExtension", pos="first")
    self.app.add_hook("after_initialize",
                      self.on_after_initialize,
                      name = "StaticFileExtension", pos="first")

  def get_normalized_abs_path(self, path):
    return os.path.join(self.path, path.replace("..", ""))

  def hash_func(self, abs_path):
    hasher = sha1()
    with open(abs_path) as io:
      stat = os.stat(abs_path)
      hasher.update(b_(abs_path))
      hasher.update(b_(stat.st_mtime))
      hasher.update(b_(stat.st_size))
    return hasher.hexdigest()[:16]

  def calc_hash(self, abs_path):
    with self.lock:
      if not abs_path in self.hashes:
        self.hashes[abs_path] = self.hash_func(abs_path)
    return self.hashes.get(abs_path, None)

  def on_before_initialize(self):
    self.hashes = {}

    @self.app.get(self.url+"(str:.*)")
    def static_file(*a):
      path = self.app.req.params[-1]
      abs_path = self.get_normalized_abs_path(path)

      if self.cache > -1:
        self.app.res.set_header("Expires", datetime.utcnow() + \
                                   timedelta(seconds=self.cache))
        self.app.res.set_header("Cache-Control", "max-age=" + u_(self.cache))
      else:
        self.app.res.set_header("Cache-Control", "public")

      if_modified_since = self.app.req.env.get("HTTP_IF_MODIFIED_SINCE", None)
      if if_modified_since:
        ims_d = parse_http_date_string(if_modified_since)
        mt_d  = datetime(*(tuple(time.gmtime(os.stat(abs_path).st_mtime))[:6]))
        if ims_d >= mt_d:
          self.app.res.not_modified()

      self.app.res.send_file(abs_path)

  def on_after_initialize(self):
    old_url = self.app.get_url_builder("static_file")
    def new_url(path, _query=None):
      if self.cache > -1:
        hash = self.calc_hash(self.get_normalized_abs_path(path))
        if hash:
          return old_url(path, _query=hash)
      return old_url(path)
    del self.app.url_cache["static_file"]
    self.app.url_cache["static_file"] = new_url

#}}}

class AsyncExtension(Extension): # {{{
  """Asynchronous request extension(requires gevent, greenlet).

  See "Asynchronous applications" for further documentations.
  """
  def __init__(self, app):
    Extension.__init__(self, app)
    app._send_back_response = self._send_back_response
    self.on_connection_close_handler = lambda *a : None
    import gevent.socket
    import gevent.queue
    original_sendall = gevent.socket.socket.sendall
    def sendall(*args):
      try:
        return original_sendall(*args)
      except gevent.socket.error:
        if isinstance(self.app.res.content, gevent.queue.Queue):
          self.on_connection_close_handler(True)
        raise
    gevent.socket.socket.sendall = method_type(sendall, None, gevent.socket.socket)

  def _send_back_response(self, response):
    import gevent.queue
    content = response.content
    if isinstance(content, gevent.queue.Queue):
      first_item = content.get()
      response.start_response()
      return self._result_generator(first_item, content)
    else:
      response.start_response()
      return self.app.convert_content(content)

  def _result_generator(self, first, rest):
    yield self.app.convert_content(first)[0]
    for v in rest: yield self.app.convert_content(v)[0]

  def __call__(self, f):
    """Makes the given action a Non-blocking, asynchronous action."""
    import gevent.queue
    @functools.wraps(f)
    def _(*args, **kw):
      self.app.res.content = gevent.queue.Queue()
      f(*args, **kw)
      return self.app.res.content
    return _

  def write(self, data):
    """Writes the given chunk to the current output buffer."""
    self.app.res.content.put(data)

  def finish(self):
    """Flushes the current output buffer to the client."""
    if self.app.res.content.empty():
      self.write(u_(""))
    self.on_connection_close_handler(False)
    self.write(StopIteration)

  def on_connection_close(self, f):
    """Register a handler function to be called when the connection is closed."""
    self.on_connection_close_handler = f

  def callback(self, f):
    """Adds thread-local data and exception handling functions to the given function."""
    tls = self.app.copy_tls_property()
    def _(*args, **kw):
      self.app.copy_tls_property(tls)
      try:
        f(*args, **kw)
      except Exception as e:
        old_content = self.app.res.content
        self.app._handle_exception(self.app.res, e)
        old_content.put(self.app.res.content)
        self.app.res.content = old_content
        self.finish()
    return _

#}}}

#}}}

