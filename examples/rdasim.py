#!/usr/bin/env python
#
# A simple RDA server emulator. Sends noisy sinusoids to a client with a 
# specified sampling frequency and other parameters
# 
# The gaussian noise is added to the signals. The noise standart deviation
# increases from 0 on the channel 0, to 'noise_scale' on the last channel

import socket
import rdadefs as defs
import ctypes as c
import numpy as np
import time
import argparse

__author__ = "Dmytro Bielievtsov"
__email__ = "belevtsoff@gmail.com"

docstring = "A simple RDA server emulator. Sends noisy sinusoids to a client with a\n \
specified sampling frequency and other parameters\n \
\n \
The gaussian noise is added to the signals. The noise standart deviation\n \
increases from 0 on the channel 0, to 'noise_scale' on the last channel\n"

parser = argparse.ArgumentParser(docstring)
parser.add_argument('sfreq', nargs='?', type=float, help='sampling frequency', default=500.)
parser.add_argument('bsize', nargs='?', type=int, help='block size', default=10)
parser.add_argument('sigfreq', nargs='?', type=float, help='signal frequency', default=20.)
parser.add_argument('nchannels', nargs='?', type=int, help='number of channels', default=4)
parser.add_argument('amp', nargs='?', type=float, help='signal amplitude', default=1.)
parser.add_argument('nscale', nargs='?', type=float, help='noise scale', default=0.4)

parser.add_argument('--port', nargs='?', type=int, help='server port', default=51244)

args = parser.parse_args()

#------------------------------------------------------------------------------ 

nChannels = args.nchannels
sampling_freq = args.sfreq
blockSize = args.bsize

signal_freq = args.sigfreq
signal_amp = args.amp
noise_scale = args.nscale

HOST = ''               # Symbolic name meaning all available interfaces
PORT = args.port            # RDA float32 port

#------------------------------------------------------------------------------
# start msg

def create_start_msg(nChannels, sampling_freq):
    dResolutions = np.ones(nChannels)
    dResolutions = (c.c_double * nChannels).from_buffer(dResolutions)
    sChannelNames = "".join([str(ch) + '\x00' for ch in range(1, nChannels + 1)])
    sChannelNames = c.create_string_buffer(sChannelNames)
    sChannelNames = (c.c_ubyte * len(sChannelNames)).from_buffer(sChannelNames)
    
    start_msg = defs.rda_msg_start_t.full(nChannels, c.sizeof(sChannelNames))()
    start_msg.hdr = defs.rda_msg_hdr_t()
    start_msg.hdr.guid = defs.RDA_GUID
    start_msg.hdr.nSize = c.sizeof(start_msg)
    start_msg.hdr.nType = defs.RDA_START_MSG
    start_msg.nChannels = nChannels
    start_msg.dSamplingInterval = 1. / sampling_freq
    start_msg.dResolutions = dResolutions
    start_msg.sChannelNames = sChannelNames
    
    return start_msg

# stop msg

def create_stop_msg():
    stop_msg = defs.rda_msg_stop_t()
    stop_msg.hdr = defs.rda_msg_hdr_t()
    stop_msg.hdr.guid = defs.RDA_GUID
    stop_msg.hdr.nSize = c.sizeof(stop_msg)
    stop_msg.hdr.nType = defs.RDA_STOP_MSG
    
    return stop_msg
    
# data msg

def create_data_msg(data, nBlock):
    nPoints, nChannels = data.shape
    
    data_msg = defs.rda_msg_data_t.full(nChannels, nPoints, 0)()
    data_msg.hdr = defs.rda_msg_hdr_t()
    data_msg.hdr.guid = defs.RDA_GUID
    data_msg.hdr.nSize = c.sizeof(data_msg)
    data_msg.hdr.nType = defs.RDA_FLOAT_MSG
    data_msg.nBlock = nBlock
    data_msg.nPoints = nPoints
    data_msg.nMarkers = 0
    data_msg.fData = (c.c_float * (nChannels * nPoints)).from_buffer(data.flatten())
    
    return data_msg

def create_sig(timearr, nChannels, signal_freq, signal_amp, noise_scale):
    sig = np.sin(2 * np.pi * signal_freq * timearr) * signal_amp / 2
    noise = np.random.normal(scale=noise_scale, size=(len(sig), nChannels))
    noise = noise * np.linspace(0, 1, nChannels)
    
    return (np.array([sig]).T + noise).astype('float32')

#------------------------------------------------------------------------------
# Ctrl+C handling

import signal
import sys

def exit(signal, frame):
        if signal: print 'Caught Ctrl+C, stopping...'
        global conn
        conn.send(create_stop_msg())
        conn.close()
        sys.exit(0)
        
signal.signal(signal.SIGINT, exit)


#------------------------------------------------------------------------------
# main loop

global conn

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
conn, addr = s.accept()

print 'Connected by', addr
start_msg = create_start_msg(nChannels, sampling_freq)
conn.send(start_msg)

nBlock = 0

while True:
    send_start = time.time()
    
    tstart = nBlock * blockSize / sampling_freq
    tstop = ((nBlock + 1) * blockSize - 1) / sampling_freq
    timearr = np.linspace(tstart, tstop, blockSize)
    sig = create_sig(timearr, nChannels, signal_freq, signal_amp, noise_scale)
    
    data_msg = create_data_msg(sig, nBlock)
    conn.send(data_msg)
    nBlock += 1
    
    send_end = time.time()
    
    time.sleep(max(0, blockSize / sampling_freq - (send_end - send_start)))
    now = time.time()

exit(None, None)
