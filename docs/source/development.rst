Development
======================

This document describes how to develop the rays itself. 
rays uses the following libraries for development.

:distribute:
    Distribute is a fork of the Setuptools project.

:virtualenv:
    virtualenv is a tool to create isolated Python environments.

:tox:
    Tox is a generic virtualenv management and test command line tool.

:py.test:
    py.test provides simple powerful testing with Python.

:WebTest:
    webtest is a Helper to test WSGI applications.

:Sphinx:
    Sphinx is a tool that makes it easy to create intelligent and beautiful documentation.

Get resources
----------------

::

    cd yourworkspace
    git clone git@github.com:yourname/rays.git

Install libraries
-------------------------------------

::

    easy_install distribute
    easy_install vitrualenv
    easy_install tox

Create your own test environment
----------------------------------------------

::

    cd rays
    cp tox.ini.sample tox.ini
    vi tox.ini
    (make some configurations...)
    tox

Now, you have isolated environments including all dependencies.
To activate this environment, on OS X and Linux, do the following commands::

    $ . .tox/py27/bin/activate

You can also active python3 environments, do the following commands::

    $ . .tox/py32/bin/activate

On Windows, do the following command::

    $ .\.tox\py27\scripts\activate.bat

Run tests
------------

::

    cd rays
    tox

You should see test results and test coverage results.

Write documents
-----------------
Document source files are written using reStructuredText. These sources are converted to HTML files using the sphinx.

rays project has 2 branches: 

1. gh-pages: Generated HTML files.
2. master  : Any other files(including document source files).

Document source files are stored under the ``master`` branches::

    master +
           - src
           - setup.py
           - (other files and directories)
           - docs
               +
               - sources <- document source files

``master`` branch contains the ``gh-pages`` as a subdirectory.(git submodules)::

    master +
           - setup.py
           - src
           - (other files and directories)
           - docs +
                  - sources <- document source files
                  - build +
                          - html <- link to the gh-pages branch

Pulling down the ``gh-pages`` as a submodule is the following command::

    python setup.py doc_init_submodule

Now ready to generate HTML files.To generate HTML files, do the following command::

    python setup.py doc_generate

Commit and push the documents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    cd docs/build/html
    git commit -am "update docs"
    git push origin gh-pages
    cd ROOT
    git commit -am "update gh-pages submodule"
    git push origin master



