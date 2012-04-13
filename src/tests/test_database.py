#vim: fileencoding=utf8
from __future__ import division, print_function

import sys
import sys
from datetime import datetime
import time
import threading
import os.path
from random import Random

from rays import *
from rays.compat import *
from .base import *

import pytest

class Parent(Model):
  table_name = "parents"

  def class_init(cls):
    Model.class_init(cls)
    cls.reference_class("Parent1", lambda : Parent)
    cls.reference_class("Parent2", lambda : Parent)

    @cls.hook("before_create")
    def before_create(self):
      self.created_at = datetime.now()

class Child(Model):
  table_name = "children"

  def class_init(cls):
    Model.class_init(cls)

    @cls.hook("before_create")
    def before_create(self):
      self.created_at = datetime.now()

class TestDatabase(Base):
  DB_FILE = os.path.join(Base.TEST_DIR, "test.db")

  def setup_method(self, method):
    Base.setup_method(self, method)
    try:
      os.remove(self.DB_FILE)
    except:
      pass
    app = self.app
    if "declarative" in method.__name__:
      transaction = "commit_on_success"
    else:
      transaction = "programmatic"
    app.config("DatabaseExtension", {"connection":self.DB_FILE, "transaction":transaction})
    self.db = app.ext.database.create_new_session()
    self.db.autocommit = True
    try:
      self.db.execute(""" CREATE TABLE parents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        p_id1 INTEGER,
        p_id2 INTEGER,
        created_at TIMESTAMP); """ )
      self.db.execute(""" CREATE TABLE  children(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER NOT NULL,
        name TEXT,
        created_at TIMESTAMP); """ )
      self.db.execute(""" CREATE INDEX  parent_id_idx on children(parent_id)""" )
    except:
      pass
    self.db.load_schema()
    self.db.autocommit = False

  def teardown_method(self, method):
    Base.teardown_method(self, method)
    self.db.autocommit = True
    self.db.execute("DELETE from parents")
    self.db.execute("DELETE from children")
    self.db.close()
    os.remove(self.DB_FILE)

  def test_programmatic_transaction(self):
    try:
      with self.db.transaction():
        parent1 = Parent(name="parent1")
        self.db.insert(parent1)
        raise Exception()
    except:
      selected = self.db.select_one([Parent], cond="name=?", values=["parent1"])
      assert None == selected
    else:
      assert False
  
    self.db.begin()
    parent2 = Parent(name="parent2")
    self.db.insert(parent2)
    self.db.rollback()
    selected = self.db.select_one([Parent], cond="name=?", values=["parent2"])
    assert None == selected
  
    self.db.begin()
    parent3 = Parent(name="parent3")
    self.db.insert(parent3)
    self.db.commit()
    selected = self.db.select_one([Parent], cond="name=?", values=["parent3"])
    assert "parent3" == selected.name
  
  def test_declarative_transaction(self):
    app = self.app
  
    @app.get("success")
    def success():
      parent1 = Parent(name="parent1")
      app.db.insert(parent1)
      return ""
  
    @app.get("error")
    def error():
      parent2 = Parent(name="parent2")
      app.db.insert(parent2)
      app.res.internal_error()
    self.finish_app_config()
  
    self.browser.get(self.url("success"))
    selected = list(self.db.select([Parent]))
    assert 1 == len(selected)
    assert "parent1" == selected[0].name
  
    try:
      self.browser.get(self.url("error"))
      assert False
    except Exception as e:
      selected = list(self.db.select([Parent]))
      assert 1 == len(selected)
      assert "parent1" == selected[0].name
  
  
  def test_insert(self):
    with self.db.transaction():
      parent1 = Parent(name=u_("親1"))
      parent2 = Parent(name="parent2")
      self.db.insert(parent1)
      self.db.insert(parent2)
  
    assert parent1.created_at
    selected = self.db.select_one([Parent], cond="id=?", values=[parent1.id])
    assert selected.name == parent1.name
    selected = self.db.select_one([Parent], cond="id=?", values=[parent2.id])
    assert selected.name == parent2.name
  
  
  def test_update(self):
    with self.db.transaction():
      parent1 = Parent(name="parent1")
      self.db.insert(parent1)
      parent1.name = "change"
      self.db.update(parent1)
  
    selected = self.db.select_one([Parent], cond="id=?", values=[parent1.id])
    assert "change" == selected.name

  def test_save(self):
    with self.db.transaction():
      parent1 = Parent(name="parent1")
      self.db.save(parent1)
      parent1.name = "change"
      self.db.save(parent1)
  
    selected = self.db.select_one([Parent], cond="id=?", values=[parent1.id])
    assert "change" == selected.name
  
  def test_delete(self):
    with self.db.transaction():
      parent1 = Parent(name="parent1")
      parent2 = Parent(name="parent2")
      self.db.insert(parent1)
      self.db.insert(parent2)
  
    self.db.delete(parent1)
    selected = list(self.db.select([Parent], cond="1"))
    assert 1 == len(selected)
    assert parent2.name == selected[0].name
  
  def test_select(self):
    with self.db.transaction():
      parent1 = Parent(name="parent1")
      parent2 = Parent(name="parent2")
      self.db.insert(parent1)
      self.db.insert(parent2)
      parent3 = Parent(name="parent3", p_id1=parent1.id, p_id2=parent2.id)
      self.db.insert(parent3)
  
      child1 = Child(name="child1", parent_id=parent1.id)
      child2 = Child(name="child2", parent_id=parent1.id)
      child3 = Child(name="child3", parent_id=parent2.id)
      self.db.insert(child1)
      self.db.insert(child2)
      time.sleep(1)
      self.db.insert(child3)
  
    selected = self.db.select_one([Parent], cond="name=?", values=["parent1"])
    assert parent1.name == selected.name

    assert repr(parent1).startswith("<Parent ")
  
    selected = list(self.db.select([Child], cond="parent_id=?", values=[parent1.id]))
    assert 2 == len(selected)
  
    selected = list(self.db.select([Child, Parent], 
      cond="Parent.id=Child.parent_id and  parent_id=?", values=[parent2.id]))
    assert 1 == len(selected)
    assert parent2.name == selected[0].parent.name
    assert child3.name == selected[0].child.name
  
    selected = list(self.db.select([Parent, Parent.Parent1, Parent.Parent2], 
      cond="Parent.p_id1 = Parent1.id and Parent.p_id2 = Parent2.id and Parent.id=?",
      values=[parent3.id]))
    assert 1 == len(selected)
    assert parent2.name == selected[0].parent2.name
    assert parent1.name == selected[0].parent1.name
  
    selected = list(self.db.select([Child], cond="1 order by created_at desc"))
    assert child3.id == selected[0].id
