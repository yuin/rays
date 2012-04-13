from rays import *

class Test1Extension(Extension):
  def __init__(self, app, name):
    Extension.__init__(self, app)
    self.name = name
