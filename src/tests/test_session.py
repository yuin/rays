#vim fileencoding=utf8
from __future__ import division, print_function

import sys, time, os
from copy import copy

from rays import *
from rays.compat import *
from .base import *

import pytest

class SessionBase(Base):
  DB_FILE = os.path.join(Base.TEST_DIR, "test.db")

  def add_routes(self):
    app = self.app

    @app.get("session/set")
    def session_set():  
      assert app.session is not None
      app.session["test_string"] = "test"
      app.session["test_list"] = [1,2,3]
      app.session["test_dict"] = {"test":"value"}
      return ""
  
    @app.get("session/get1")
    def session_get1():  
      assert "test" == app.session["test_string"]
      assert [1,2,3] == app.session["test_list"]
      assert {"test":"value"} == app.session["test_dict"]
      return ""
  
    @app.get("session/get2")
    def session_get2():  
      assert 0 == len(app.session)
      assert None == app.session.session_id
      return ""
  
    @app.get("session/get3")
    def session_get3():  
      assert None == app.session["test_string"]
      return ""
  
    @app.get("session/kill")
    def session_kill():  
      app.session.kill()
      assert 0 == len(app.session)
      assert True == app.session.killed
      return ""
  
    @app.get("path")
    def session_path():  
      assert (not app.session)
      return ""
  
    @app.get("session/clear")
    def session_clear():  
      app.res.set_cookie(app.ext.session.cookie_name, "", -10000, path="/session")
      app.session.clear()
      return ""

    @app.get("session/error")
    def session_error():
      raise Exception()
  
  def test_basic_session_behaviour(self):
    app = self.app

    config = copy(self.base_session_config)
    app.config([("SessionExtension", config)])
    self.add_routes()
    self.finish_app_config()
  
    self.browser.get(self.url("session_set"))
    self.browser.get(self.url("session_get1"))
    self.browser.get(self.url("session_kill"))
    self.browser.get(self.url("session_get2"))
    self.browser.get(self.url("session_path"))

  def test_out_of_date_session_is_killed(self):
    app = self.app

    config = copy(self.base_session_config)
    config["expires"] = 1 # expire sessions after 1 second
    app.config([("SessionExtension", config)])
    self.add_routes()
    self.finish_app_config()
  
    self.browser.get(self.url("session_set"))
    time.sleep(1.5)
    self.browser.get(self.url("session_get3"))

  def test_same_session_exists_within_given_expire_time(self):
    app = self.app

    config = copy(self.base_session_config)
    config["expires"] = 3 
    app.config([("SessionExtension", config)])
    try:
      app.config("DatabaseExtension", {"connection":os.path.join(self.TEST_DIR, "test.db"), "transaction":"commit_auto"})
    except:
      pass
    self.add_routes()
    self.finish_app_config()
  
    
    self.browser.get(self.url("session_set"))
    self.browser.get(self.url("session_clear"))
    self.browser.get(self.url("session_set"))

    app.db = app.ext.database.create_new_session()
    try:
      time.sleep(4)
      self.browser.get(self.url("session_clear"))
      self.browser.get(self.url("session_set"))
    finally:
      app.db.close()
  
    app.db = app.ext.database.create_new_session()
    try:
      app.ext.session.cleanup()
      assert 1 == app.ext.session.count()
    finally:
      app.db.close()

  def test_session_does_not_exists_if_error_has_occurred(self):
    app = self.app

    config = copy(self.base_session_config)
    app.config([("SessionExtension", config)])
    try:
      app.config("DatabaseExtension", {"connection":os.path.join(self.TEST_DIR, "test.db"), "transaction":"commit_auto"})
    except:
      pass
    self.add_routes()
    self.finish_app_config()
  
    
    self.browser.get(self.url("session_error"), expect_errors=True)
    app.db = app.ext.database.create_new_session()
    try:
      assert 0 == app.ext.session.count()
    finally:
      app.db.close()

  def test_reject_tamperred_requests(self):
    app = self.app

    config = copy(self.base_session_config)
    config["expires"] = 1 # expire sessions after 1 second
    app.config([("SessionExtension", config)])
    try:
      app.config("DatabaseExtension", {"connection":os.path.join(self.TEST_DIR, "test.db"), "transaction":"commit_auto"})
    except:
      pass
    self.add_routes()
    self.finish_app_config()
  
    
    self.browser.get(self.url("session_set"))
    self.browser.set_cookie(app.ext.session.cookie_name, "tampered")
    with pytest.raises(AssertionError):
      self.browser.get(self.url("session_get1"))

  
class TestFileSession(SessionBase):
  SESSION_DIR = os.path.join(Base.TEST_DIR, "sessions")

  def setup_method(self, method):
    SessionBase.setup_method(self, method)

    self.base_session_config = {
      "store":"File", 
      "secret":"aaaaaaaaaaaaaaaa", 
      "cookie_name":"test_cookie", 
      "cookie_path":"session",
      "root_path":os.path.join(self.TEST_DIR, "sessions") 
    }

    if os.path.exists(self.SESSION_DIR):
      for file in os.listdir(self.SESSION_DIR):
        self.try_removing_file(os.path.join(self.SESSION_DIR, file))

  def teardown_method(self, method):
    if os.path.exists(self.SESSION_DIR):
      for file in os.listdir(self.SESSION_DIR):
        self.try_removing_file(os.path.join(self.SESSION_DIR, file))
      os.rmdir(self.SESSION_DIR)

class TestDatabaseSession(SessionBase):
  def setup_method(self, method):
    SessionBase.setup_method(self, method)

    app = self.app
    self.try_removing_file(self.DB_FILE)

    app.config("DatabaseExtension", {"connection":os.path.join(self.TEST_DIR, "test.db"), "transaction":"commit_auto"})
    db_session =  app.ext.database.create_new_session()
    db_session.autocommit = True
    db_session.execute(DatabaseSessionStore.SCHEMA)
    db_session.execute(DatabaseSessionStore.INDEX)
    db_session.close()

    self.base_session_config = {
      "store":"Database", 
      "secret":"aaaaaaaaaaaaaaaa", 
      "cookie_name":"test_cookie", 
      "cookie_path":"session"
    }

  def teardown_method(self, method):
    app = self.app
    self.try_removing_file(self.DB_FILE)

    SessionBase.teardown_method(self, method)

class TestSessionStoreBase(Base):
  def test_error_if_session_secret_is_null(self):
    with pytest.raises(ValueError):
      self.app.config("SessionExtension", {
      "store":DatabaseSessionStore, 
      "cookie_name":"test_cookie", 
      "cookie_path":"session"}) # does not have a value whose key is a "secret".

  def test_abstract_methods(self):
    obj = SessionStoreBase(self.app, "secret")
    with pytest.raises(NotImplementedError):
      obj.exists("dummy")
    with pytest.raises(NotImplementedError):
      obj.create()
    with pytest.raises(NotImplementedError):
      obj.save("dummy")
    with pytest.raises(NotImplementedError):
      obj.load("dummy")
    with pytest.raises(NotImplementedError):
      obj.delete("dummy")
    with pytest.raises(NotImplementedError):
      obj.cleanup()
    with pytest.raises(NotImplementedError):
      obj.count()
    


