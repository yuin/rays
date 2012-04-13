import multiprocessing
import sys
import os.path

workers = multiprocessing.cpu_count() * 2 + 1
daemon = True
pidfile = os.path.abspath(os.path.join(os.path.dirname(__file__), "gunicorn.pid"))

accesslog = "-"
errorlog  = "-"
