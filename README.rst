Overview
===================

* rays is a WSGI compatible web framework designed for small web applications.
* rays supports python2.6, 2,7, 3.2, 3.3 .
* rays handles multibyte-charcters correctly(It is important for me, So I'm a Japanese).

Features
--------
* Routings: Simple, but powerful.
    * Routes are defined by regular expressions and type constructors::

        @app.get("member/(int:\d+)")
        def show_member(member_id):
          # ...

    * ``app.url`` has easy reference to routes::

        app.url.show_member(1) #=> "http://somehost/member/1"

* Filters and Hooks: Writing DRY code.
    * Hooks will be called back at following hook points.
        * `before_initialize()`
        * `after_initialize()`
        * `before_call(env, start_response)`
        * `before_dispatch()`
        * `before_action()`
        * `before_start_response()`
        * `after_load_extension(name, extension)`
        * `after_connect_database(database)`

    * Hooks example::

        @app.hook("before_start_response")
        def status_log_hook():
          if app.res.is_success:
            app.logger.info("success")
          elif app.res.is_abort:
            app.logger.warn("abort")
          else:
            app.logger.error("error:%s"%unicode(app.res.exception))

    * Filters enable actions to run pre- and post-processing code::

        def filter(*args):
          # pre-processing
          yield
          # post-processing
        
        with app.filter(filter):
          @app.get("member/(int:\d+)")
          def show_member(member_id):
            # ...

* Templates: Fast and flexible.
    * To render ``index.html``, ``app.renderer.index(vars)``.
    * Strings surrounded by "<%" and "%>" will be interpreted as a python code.
        * ``<% a = 10 %>``
    * ``<%= python code %>`` will be replaced by the result of executing "python code".
    * Always applys a filter(i.e. ``cgi.escape``). To turn it off, use ``<%=r python code %>``
    * Many way to express blocks::

       <%- for i in xrange(10): -%>
         <%= a %>
         <% %>
       
       <%- for i in xrange(10) {: -%>
         <%= a %>
       <% :} %>
       
       <%- for i in xrange(10) : -%>
         <%= a %>
       <% end %>
       
    * Integrated useful template helpers::

        <% with h.capture("body"): %>
          foo
          <% %>
        <%= body %>

* ORMs: Simple wrapper for built-in sqlite3 module.::

    result = app.db.select([Site, Page], cond="Page.site_id=Site.id and Page.id = ?", values=[1])
    print(result[0].site)
    print(result[0].page)
    app.db.insert(page)
    app.db.update(page)
    app.db.delete(page)
    app.db.shell() # interactive sqlite3 shell

* Sessions::

    @app.get("signin")
    def signin():
      if app.req.input["name"] == "bob" and app.req.input["password"] == "abracadabra":
        app.session.kill()
        app.session["authorized"] = True
      else:
        # ...

* WebSockets: Realtime messaging. ( **requires gevent, greenlet, gevent-websocket** )
    * You can find these source code in the `src/samples/websocketchat`_ directory. ::

        @app.get("chat")
        def chat():
          ws = app.req.websocket
          SOCKETS.add(ws)
          app.logger.info("accepts: %s"%repr(ws.socket))
        
          while True:
            msg = ws.receive()
            if msg is None:
              break
        
            error_sockets = set([])
            for s in SOCKETS:
              try:
                s.send(msg)
              except Exception, e:
                error_sockets.add(s)
        
            for s in error_sockets:
              SOCKETS.remove(s)

Asynchronous applications
~~~~~~~~~~~~~~~~~~~~~~~~~

(TODO, See `src/samples/asynchronous`_)

Extensions
-------------------------
rays has API that allows developers to add new features to their applications.
This api is consistent with 2 classes: ``rays.ExtensionLoader`` and ``rays.Extension``.

To install your extensions, you need to configure the ``rays.ExtensionLoader``.

index.py::

    import extensions

    app.config([
      ("ExtensionLoader", {"module": extensions }),
    ])

``extensions`` is a module that has group of extensions.::

    root
    |---- index.py
    |---- extensions
               |---- __init__.py
               |---- cache_extension.py
               |---- template_extension.py
               .
               .
               .


Creating your extension
~~~~~~~~~~~~~~~~~~~~~~~

(TODO)


Requirements
-------------

* Python 2.6
* Python 2.7 
* Python 3.2
* Python 3.3

Installation
-------------

``easy_install rays``

or 

``pip install -e git://github.com/yuin/rays.git#egg=rays``

or download a zip file from ``https://github.com/yuin/rays/zipball/master`` and ::

    python setup.py install

Example
------------
You can find these source code in the `src/samples/blog`_ directory.

index.py::


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


.. _`src/samples/websocketchat`: https://github.com/yuin/rays/tree/master/src/samples/websocketchat
.. _`src/samples/asynchronous`: https://github.com/yuin/rays/tree/master/src/samples/asynchronous
.. _`src/samples/blog`: https://github.com/yuin/rays/tree/master/src/samples/blog
