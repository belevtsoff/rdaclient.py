#!/usr/bin/env python
#
# Receives the data from the RDA server and calculates it's FFT. The spectrum
# is calculated within a sliding window. Power of delta, alpha, beta and gamma
# bands are calculated plotted in real-time.
#
# For a first time, try using rdasim.py as a server:
# ./rdasim 200 10 20

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

address = ('', 51244)   # server address
window = 500            # plotting window (samples)
channel = args.chan     # channel to plot

real_width = True       # whether to show real band widths
delta = [0.1, 4]        # frequency bands (Hz)
alpha = [8., 12]
beta = [12., 30]
gamma = [25., 100]

#------------------------------------------------------------------------------ 

# creating a client
client = rc.Client(buffer_size=300000, buffer_window=window)
client.connect(address)
client.start_streaming()

# get sampling frequency
sample_interval = client.start_msg.dSamplingInterval/1e6 # seconds
sampling_freq = 1.0 / sample_interval

# calculate bands
widths = np.array([delta[1] - delta[0],
                   alpha[1] - alpha[0],
                   beta[1] - beta[0],
                   gamma[1] - gamma[0]])

x = np.array([delta[0] + widths[0] / 2,
              alpha[0] + widths[1] / 2,
              beta[0] + widths[2] / 2,
              gamma[0] + widths[3] / 2])

# starting gnuplot
g = os.popen('gnuplot', 'w')

# set up gnuplot
print >> g, 'set terminal x11'
print >> g, 'set yrange [0:250]'

if real_width:
    print >> g, 'set xrange [0:%s]' % max(gamma)
    print >> g, 'set xlabel \"frequency, Hz\"'
else:
    print >> g, 'set xlabel \"delta, alpha, beta, gamma\"'
    print >> g, 'set xrange [0.5:4.5]'
    
print >> g, 'set ylabel \"power\"'
print >> g, 'set grid'
g.flush()

def boxplot(g, data):
    '''
    Plots the data with gnuplot
    
    Args:
        g: pipe to gnuplot
        data: data with three columns: x, y, width
            
    '''
    print >> g, 'plot \'-\' with boxes\n'
    for d in data:
        print >> g, '%s %s %s\n' % tuple(d)
    print >> g, 'e\n'
    g.flush()
    

def run_fft():
    lastidx = None
    while client.is_streaming:
        sig = client.poll(window) # wait for new data
                
        if sig is not None:
            sig = sig[:, channel]
            
            # calculate FFT
            freq = np.fft.fftfreq(len(sig), sample_interval)
            spec = np.abs(np.fft.fft(sig)) ** 2
            
            # integrate
            bands = np.array([np.sqrt(np.sum(spec[(freq > delta[0]) & (freq <= delta[1])])),
                              np.sqrt(np.sum(spec[(freq > alpha[0]) & (freq <= alpha[1])])),
                              np.sqrt(np.sum(spec[(freq > beta[0]) & (freq <= beta[1])])),
                              np.sqrt(np.sum(spec[(freq > gamma[0]) & (freq <= gamma[1])]))])
            
            if not real_width:
                loc_x = np.arange(1, 5)
                loc_widths = np.ones(4)
            else:
                loc_x = x
                loc_widths = widths
            
            data = np.vstack((loc_x, bands, loc_widths)).T # stack x, y and width in a single matrix

            boxplot(g, data) # plot

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

run_fft()



