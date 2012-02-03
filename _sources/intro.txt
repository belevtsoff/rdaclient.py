Introduction
============

What is rdaclient.py?
---------------------
Rdaclient.py is an asynchronous RDA client with buffer, written in pure python (with extensive usage of ctypes). Remote Data Access protocol is used by the the BrainVision recording software to share EEG the data over the network.

For BrainAmp (by Brain Products) users, the module is aimed to simplify the development of processing applications (including BCIs) by encapsulating an asynchronous network client and a circular buffer in a single module. For more information, refer to :doc:`details`.


Installation
------------

Before installing, make sure you have the following:

* python 2.6
* numpy 1.4.1 or higher

Optionally, for the tutorial/examples, you'll need:

* matplotlib
* gnuplot <-- ordinary binary, not a python package

Next, get the source from the github::

    cd /where/you/want/it/to/be
    git clone git://github.com/belevtsoff/rdaclient.py.git
    cd rdaclient.py/
    
This is basically it. In order to make modules importable from other locations, just add the source folder to your PYTHONPATH, e.g.::

    echo export PYTHONPATH=\$PYTHONPATH:/path/to/rdaclient.py/src/ >> ~/.bashrc

substituting :file:`/path/to/rdaclient.py/` with the actual absolute path to :file:`rdaclient.py/`



