# rvnstats
Provides a very simple API to get basic stats on Ravencoin

Written in Python.

Depends on:
* Python
  * Flask
  * requests
* A local RVN node
* Cryptoscope.io API


'''
pip install gunicorn
gunicorn -D -w 4 -b 0.0.0.0:80 rvnstats:app
'''
