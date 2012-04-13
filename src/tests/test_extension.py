#vim fileencoding=utf8
from __future__ import division, print_function

import sys, os.path
from rays import *
from rays.compat import *
from .base import *
import extensions

import pytest

class TestExtension(Base):
  def test_extension_loader(self):
    app = self.app
    app.config([
      ("ExtensionLoader", {"module": extensions }),
      ("TestExtension", {"name": "aaa"})
    ])
    self.finish_app_config()
  
    assert app.ext.test
    assert "aaa" == app.ext.test.name
    assert (not app.ext.test1)
  
    with pytest.raises(NameError):
      app.config("Test1Extension", {"name": "aaa"})
