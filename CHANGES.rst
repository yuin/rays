Changes
============
0.4.2 (Sep 16, 2013):
--------------------------------------------
- Improved: rays considers python3 as a **mainstream** python. New compat.py module provides the python3 forward compatibility.
- Improved: SessionExtension now can take a SessionStoreBase class as a parameter.

0.4.1 (May 10, 2013):
--------------------------------------------
- Improved: **rays now supports Python3.3 .**
- Fixed: Application#filter applies filters with unexpected order
- Fixed: ExtensionLoader tries to load non modile directories
- Fixed: can not upload multiple files.
- Fixed: Model class should call HookableClass#class_init.
- Improved: Database.execute now can take a without_transaction option.
- New: Application#generate_javascript_url_builder
- New: a new hook point(after_load_extension, after_connect_database)

0.4.0 (April 12, 2012):
--------------------------------------------
- Improved: **rays now supports Python3.2 .**
- Dropped:  **rays drops Python2.6> supports.**
- New: Application.logger
- New: Application.copy_tls_property
- New: Applicaiton.get_url_builder
- New: Application.serve_forever
- New: Application.run_gevent
- New: Request object supports Accept-* headers
- New: Request.websocket
- New: Request.is_xml_http_request
- New: Request.http_version
- New: Response.not_modified
- New: AsyncExtension
- Improved: app.url now supports new options, _ssl and _query .
- Improved: StaticFileExtension now use caches aggressively.
- Fixed: autoreloading does not work with ``run_simple`` . (Thanks Nobuo Okazaki)

0.3.0 (March 2, 2010):
--------------------------------------------
- New: DefaultAttrDict, A defaultdict like object, whose items also be accessible through object attributes.
- New: Context.d, a user namespace for context objects.
- New: Application.d, a user namespace for application global variables.
- New: Request.method, Request.ua
- New: Application.run_fapws
- New: without_filters. "action" functions can now be executed without calling any filters.
- New: Context.d, Application.d 
- Fixed: Database transaction bug with python2.5
- Fixed: File upload bugs
- Fixed: Embpy parser bugs
- Fixed: Autoreload bugs
- Changed: Database.select(**Backward-imcompatible**).

0.2.0 (August 15, 2009):
--------------------------------------------
- New: Session support
- New: Sample codes
- Many backward-incompatible changes

0.1.1 (July 26, 2009):
--------------------------------------------
- Improved: Muti-threading support
- New: Context.db, Context.renderer
- New: Application.create_db_session
- Removed: Application.db

0.1.0 (July 21, 2009):
-----------------------
- Initial release. 
