from rays import *

class TestExtension(Extension):
  def __init__(self, app, name):
    Extension.__init__(self, app)
    self.name = name
