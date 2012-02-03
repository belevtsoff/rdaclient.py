#!/usr/bin/env python
#
# Receives the data from the RDA server and plots the raw trace of specified
# channel in real-time.
#
# For a first time, try using rdasim.py as a server:
# ./rdasim 100 10 1

import argparse
import time
import os

import numpy as np

import rdaclient as rc

__author__ = "Dmytro Bielievtsov"
__email__ = "belevtsoff@gmail.com"

parser = argparse.ArgumentParser("raw test")
parser.add_argument('chan', nargs='?', type=int, help='channel', default=0)
args = parser.parse_args()

#------------------------------------------------------------------------------ 
# parameters

address = ('', 51244)     # server address
window = 250              # plotting window (samples)
channel = args.chan       # channel to plot

#------------------------------------------------------------------------------ 

# creating a client
client = rc.Client(buffer_size=300000, buffer_window=window)
client.connect(address)
client.start_streaming()

# get sampling frequency
sample_interval = client.start_msg.dSamplingInterval
sampling_freq = 1.0 / sample_interval

# starting gnuplot
g = os.popen('gnuplot --persist', 'w')

# set up gnuplot
print >> g, 'set terminal x11'
print >> g, 'set yrange [-1:1]'
print >> g, 'set xlabel \"sample\"'
print >> g, 'set ylabel \"signal\"'
print >> g, 'set grid'

g.flush()


def plot(g, data, with_):
    '''
    Plots the data with gnuplot
    
    Args:
        g: pipe to gnuplot
        data: data with two columns: x, y
        with_: plotting style (e.g. lines)
            
    '''
    sd = 'plot \'-\' w %s\n' % with_
    for d in data:
        sd += "".join(['%s ' % el for el in d])[:-1] + '\n'
    sd += 'e\n'
    print >> g, sd
    g.flush()
    

def start():
    while client.is_streaming:
        sig = client.poll(window) # wait for new data
        
        ls = client.last_sample
        x = np.arange(window) + ls - window # calculate x

        if sig is not None:
            sig = sig[:, channel] # get the whole window if possible
        else:
            sig = client.get_data(0, ls)[:, channel] # if not, get chunk
            x = np.arange(len(sig)) # correct x
        
        data = np.vstack((x, sig)).T # stack x and y in a single matrix
        
        # set an appropriate x range
        print >> g, 'set xrange [%s:%s]' % (min(x), max(max(x), window))
        
        plot(g, data, 'l') # plot

#------------------------------------------------------------------------------ 
# Ctrl + C handling

import signal
import sys

def exit(signal, frame):
        if signal: print 'Caught Ctrl+C, stopping...'
        client.stop_streaming()
        time.sleep(1)
        client.disconnect()
        sys.exit(0)
        
signal.signal(signal.SIGINT, exit)

#------------------------------------------------------------------------------ 

start()



