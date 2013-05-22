#!/usr/bin/env python
from __future__ import division, print_function
from rays import *
from rays.compat import *
import sys, os.path, math, contextlib
from datetime import datetime
import threading

app = Application()
APP_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(APP_DIR, "test.db")
c = threading.local()

app.config([
  ("debug", True),
  ("renderer", {"template_dir":os.path.join(APP_DIR, "templates"),
                "cache_dir":os.path.join(APP_DIR, "templates/caches")}),
  ("DatabaseExtension", {"connection":DB_FILE, "transaction":"commit_on_success"}),
  ("SessionExtension", {"store":"Database", "secret":"asdfeE305Gs0lg",
               "cookie_path":"admin"}),
  ("StaticFileExtension", {"url":"statics/", "path": os.path.join(APP_DIR, "statics")}),
  ("admin_name", "admin"),
  ("admin_password", "password"),
  ("blog_title", "My blog"),
  ("entry_per_page", 3),
])

class BaseModel(Model): # {{{
  def class_init(cls):
    Model.class_init(cls)

    @cls.hook("before_create")
    def before_create(self):
      self.created_at = datetime.now()
# }}}

class Entry(BaseModel): #{{{
  table_name = "entries"
  def validate(self):
    result = []
    if not self.title: result.append("Title required.")
    if len(self.title) > 100: result.append("Title too long.")
    if len(self.title) < 2: result.append("Title too short.")
    if not self.body: result.append("Body required.")
    return result
# }}}

# filters {{{
def context_setup_filter(*a, **k):
  c.title = app.vars.blog_title
  c.errors = []
  yield

def admin_filter(*a, **k):
  if not app.session["signin"]:
    app.res.redirect(app.url.admin_signin())
  yield

def flash_filter(*a, **k):
  cond = app.session["signin"]
  if cond:
    app.session["flash"] = app.session["flash"] or {}
    keys = list(iter_keys(app.session["flash"]))
  yield
  if cond:
    for key in keys: del app.session["flash"][key]
# }}}

# helpers {{{
@app.helper
@contextlib.contextmanager
def main_block(helper):
  helper.concat("<div id=\"main\">")
  with helper.capture("__main_block"):
    yield
  helper.concat(helper.captured("__main_block"))
  helper.concat("</div>")

@app.helper
def show_errors(helper, errors):
  if errors:
    helper.concat("<div class=\"error\"><strong>Error:</strong><ul>")
    for error in errors:
      helper.concat("<li>"+error+"</li>")
    helper.concat("</ul></div>")

@app.helper
def show_message(helper, message):
  if message:
    helper.concat("<div class=\"message\">")
    helper.concat(message)
    helper.concat("</div>")

@app.helper
def format_datetime(helper, dt):
  return dt.strftime("%m.%d.%y/%I%p %Z").lower()

@app.helper
def hatom_published(helper, entry):
  return """<abbr class="published" title="%s">%s</abbr>"""%(entry.created_at.isoformat(), helper.format_datetime(entry.created_at))

@app.helper
def format_body(helper, body):
  return body.replace("\n", "<br />")

@app.helper
def page_link(helper, page):
  return app.url.index()+"?page=%d"%page

@app.helper
def pagination(helper, count, page):
  page = int(page)
  n = app.vars.entry_per_page
  tpl = ["<ul id=\"pagination\">"]
  append = tpl.append
  max_page = int(math.ceil(count/float(n)))
  if page > max_page: page=1
  start, end = max(page-4, 1), min(page+4, max_page)
  append("<li class=\"%s\">%s</li>"% \
    ((page-1) < 1 and ("previous-off", "&laquo;Previous") or\
     ("previous", "<a href=\"%s\" rel=\"prev\">&laquo;Previous</a>"%(helper.page_link(c, page-1)))))
  if start != 1: append("<li><a href=\"%s\">1</a></li>"%helper.page_link(c, 1))
  if start > 2:  append("<li>&nbsp;&nbsp;.......&nbsp;&nbsp;</li>")

  for i in range(start, end+1):
    if i == page: 
      append("<li class=\"active\">%d</li>"%i)
    else:
      append("<li><a href=\"%s\">%d</a></li>"%(helper.page_link(c, i), i))

  if end < (max_page-1): append("<li>&nbsp;&nbsp;......&nbsp;&nbsp;</li>")
  if end != max_page: append("<li><a href=\"%s\">%d</a></li>"%(helper.page_link(c, max_page), max_page))
  append("<li class=\"%s\">%s</li>"% \
    ((page+1) > max_page  and ("next-off", "Next&raquo;") or\
     ("next", "<a href=\"%s\" rel=\"next\">Next&raquo;</a>"%(helper.page_link(c, page+1)))))

  append("</ul>")
  return "".join(tpl)

# }}}

# db {{{
def find_entry_by_id(entry_id):
  return app.db.select_one([Entry], cond="id=?", values=[entry_id])

def find_entries(offset, limit):
  return app.db.select([Entry], 
    cond="1 order by created_at desc limit ? offset ?",
    values=[limit, offset])

def count_entries():
  return app.db.select_one([Entry], select="SELECT count(id) as count from %(tables)s").count
# }}}

with app.filter(context_setup_filter):
  @app.get("")
  def index():
    limit = app.vars.entry_per_page
    offset = limit*(int(app.req.input.get("page", 1)) - 1)
    c.entries = find_entries(offset, limit)
    c.count   = count_entries()
    return app.renderer.show_entries({"c":c})

  @app.get("articles/(int:\d+)")
  def show_entry(entry_id):
    c.entry = find_entry_by_id(entry_id)
    c.title += " :: %s"%c.entry.title
    return app.renderer.show_entry({"c":c})

  @app.get("admin/signin")
  def admin_signin_form():
    return app.renderer.admin_signin_form({"c":c})

  @app.post("admin/signin")
  def admin_signin():
    if app.req.input["name"] == app.vars.admin_name and \
        app.req.input["password"] == app.vars.admin_password:
      app.session["signin"] = True
      app.res.redirect(app.url.admin_index())
    else:
      c.errors = ["Signin failed."]
      return app.renderer.admin_signin_form({"c":c})


  with app.filter(admin_filter, flash_filter):
    @app.get("admin")
    def admin_index():
      return app.renderer.admin_index({"c":c})

    @app.get("admin/signout")
    def admin_signout():
      app.session.kill()
      app.res.redirect(app.url.admin_signin_form())

    @app.get("admin/entry/new")
    def admin_entry_new():
      if not hasattr(c, "entry"):
        c.entry = Entry(title="", body="")
      return app.renderer.admin_entry_new({"c":c})

    @app.post("admin/entry/create")
    def admin_entry_create():
      c.entry = Entry(**app.req.input["entry"])
      c.errors = c.entry.validate()
      if c.errors:
        return admin_entry_new(c)
      app.db.insert(c.entry)
      app.session["flash"]["message"] = "Entry added."
      app.res.redirect(app.url.admin_index())

if not os.path.exists(DB_FILE):
  db = app.ext.database.create_new_session()
  db.autocommit = True
  try:
    db.execute(""" CREATE TABLE entries (
      id INTEGER PRIMARY KEY NOT NULL,
      title TEXT,
      body TEXT,
      created_at TIMESTAMP); """ )
    db.execute(DatabaseSessionStore.SCHEMA)
    db.execute(DatabaseSessionStore.INDEX)
  finally:
    db.close()

if __name__ == "__main__":
  app.serve_forever()
