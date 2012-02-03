Usage examples
==============

There are currently two example scripts available in the ``examples/`` folder:

* test_raw.py
* test_fft.py

Both of them use `gnuplot <http://www.gnuplot.info/>`_ for plotting, because it has a pretty good refresh rate. It is included in some of the popular linux distributions (e.g. Ubuntu), so check if you already have it. The data and commands are transfered from python through STDIN.

test_raw.py
-----------

This example plots the signal recorded on one of the channels (specified in the script) in a window. The window is moved and the plot is updated online, every time new data is available. For a good looking
