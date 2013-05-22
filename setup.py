#vim: fileencoding=utf8
from __future__ import division, print_function
import re, sys, os, codecs
from os.path import join, abspath, dirname
from subprocess import Popen
from contextlib import contextmanager

from setuptools import setup
from distutils.core import Command
import distutils.command as scommands

ROOT_DIR = dirname(abspath(__file__))
PACKAGE  = "rays"

# compatibility stuff {{{ 
if sys.version_info >= (3,0,0):
  unicode = str
  string_types = (unicode, bytes)
  def n_(s):
    if isinstance(s, unicode): return s
    elif isinstance(s, bytes): return s.decode("latin1")
    return unicode(s)
  getcwd = os.getcwd
else:
  bytes = str
  string_types = basestring
  def n_(s):
    if isinstance(s, bytes): return s
    elif isinstance(s, unicode): return s.encode("latin1")
    return bytes(s)
  getcwd = os.getcwdu

def b_(s, encoding='utf8'):
  if isinstance(s, unicode): return s.encode(encoding) 
  elif isinstance(s, (integer_types + (float,))): return b_(repr(s))
  return bytes(s)
def u_(s, encoding='utf8', errors='strict'):
  return s.decode(encoding, errors) if isinstance(s, bytes) else unicode(s)
# }}}

# extra commands support {{{
class _Odict(dict): keys = lambda self: sorted(dict.keys(self))
_va = dict(cmd_args={}, nssep="_")
_cmds = _Odict()
_namespace = []
_old_scommands = scommands.__all__[:]

_get_ns = lambda:_namespace and _va["nssep"].join(_namespace)+_va["nssep"] or ""
class _CommandType(type):
  def __new__(cls, class_name, class_bases, classdict):
    d = dict(user_options=[], finalize_options=lambda s:None)
    d.update(classdict)
    def _(self):
      [setattr(self,i[0].rstrip("="),None) for i in d["user_options"]]
    d["initialize_options"] = _
    d["boolean_options"] = [i for i,j,k in d["user_options"] if not i.endswith("=")]
    def _(self):
      for v in self.get_sub_commands(): self.run_command(v)
      return classdict["run"](self)
    d["run"] = _
    name = _get_ns()+class_name.lower()
    cls = type.__new__(cls, name, class_bases + (object,), d)
    cls.description = cls.__doc__ and cls.__doc__.strip() or ""
    if "sub_commands" in d:
      cls.description += "\n\tsub commands:\n"+"\n".join("\t\t"+i for i,j in d["sub_commands"])
    if name in _old_scommands and name not in scommands.__all__: scommands.__all__.append(name)
    if class_name != "Task" : _cmds[name] = cls
    return cls
Task = _CommandType('Task', (Command, ), {})

@contextmanager
def namespace(name):
  _namespace.append(name)
  yield _get_ns()
  _namespace.pop() 

# }}}

# shell utilities {{{
def xx(cmd):
  print("EXEC:(on %s)"%getcwd(), cmd)
  p = Popen(cmd, shell=True)
  p.wait()
  if p.returncode != 0:
    raise Exception("FAILED: (RET:%d)"%(p.returncode))

@contextmanager
def cd(dir):
  os.chdir(dir)
  print("EXEC: cd %s"%getcwd())
  yield

# }}}

# utilities {{{
def get_meta(name):
    path = join(ROOT_DIR, "src", PACKAGE, "__init__.py")
    text = codecs.open(path, "r", encoding="utf8", errors="ignore").read()
    return n_(re.search(r"__%s__[\s]*=[\s]*['\"]([^'\"]+)['\"]"%name, text).group(1))
# }}}

with namespace("doc") as ns: # {{{
  class init_submodule(Task): # {{{
    """Initialize a document submodule(docs/build/html)"""
    def run(self):
      with cd(ROOT_DIR):
        try:
          xx("git submodule init")
        except:
          pass
        xx("git submodule update")
      with cd(join(ROOT_DIR, "docs", "build", "html")):
        xx("git checkout -b gh-pages origin/gh-pages")
        xx("git checkout gh-pages")
      with cd(ROOT_DIR): pass

  # }}}

  class generate(Task): # {{{
    """Generate documents.""" 
    def run(self):
      with cd(ROOT_DIR):
        xx("sphinx-build -d docs/build/doctrees -b html docs/source docs/build/html")
      with cd(join(ROOT_DIR, "docs", "build", "html")):
        xx("git status")
      with cd(ROOT_DIR): pass

    sub_commands = [
      ("build", None),
      ("install", None)
    ]
  # }}}
# }}}

# test(by py.test) {{{
from setuptools.command.test import test as TestCommand
class test(Task, TestCommand):
  """run unit tests after in-place build"""
  def run(self):
    import pytest
    self.test_args = ["-rxs", "--cov-report", "term-missing", "--cov", PACKAGE, "src/tests"]
    self.test_suite = True
    pytest.main(self.test_args)

  sub_commands = [
    ("build", None),
    ("install", None)
  ]
# }}}
  
# setup {{{
development_statuses = [None,
  "Development Status :: 1 - Planning",
  "Development Status :: 2 - Pre-Alpha",
  "Development Status :: 3 - Alpha",
  "Development Status :: 4 - Beta",
  "Development Status :: 5 - Production/Stable",
  "Development Status :: 6 - Mature",
  "Development Status :: 7 - Inactive"
]

spec = dict(
  name=PACKAGE,
  version=get_meta("version"),
  url="https://github.com/yuin/"+PACKAGE,
  description='A "LESS PAIN" lightweight WSGI compatible web framework',
  long_description=open(join(ROOT_DIR, 'README.rst'), 'r').read(),
  author=get_meta("author"),
  author_email='yuin@inforno.net',
  license=get_meta("license"),
  platforms=("Platform Independent",),
  packages = [PACKAGE],
  package_dir = {PACKAGE: 'src/'+PACKAGE},
  include_package_data=True,
  zip_safe=False,
  cmdclass=_cmds,
  classifiers = [
      "Programming Language :: Python :: 2.6",
      "Programming Language :: Python :: 2.7",
      "Programming Language :: Python :: 3.2",
      "Programming Language :: Python :: 3.3",
      development_statuses[4],
      'License :: OSI Approved :: MIT License',
      'Operating System :: OS Independent',
      'Intended Audience :: Developers',
      'Topic :: Software Development :: Libraries :: Application Frameworks',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries'
      ],
  keywords = ["WSGI", "web", "framework", "cgi"],
  install_requires = [
  ],
  tests_require = [
    "pytest",
    "pytest-cov",
    "webtest",
    "requests"
  ],
  entry_points="""
  """,
)

if __name__ == "__main__":
  setup(**spec)
# }}}

