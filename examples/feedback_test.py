import numpy as np
import rdaclient as rc
import logging
import time
import pyff_client as pc

events_needed = 100
block_size = 10
threshold=-5000
wait_blocks=-3
wait=0


logging.basicConfig(level=logging.INFO, format='[%(process)-5d:%(threadName)-10s] %(name)s: %(levelname)s: %(message)s')

client = rc.Client(data_dtype = 'float32', buffer_size = 300000, buffer_window = block_size)
client.connect(('192.168.2.1', 51244))

fb = pc.pyff_client()
fb.connect()

def check_threshold(signal, threshold):
    exceeds = lambda val, th: (th>0) and (val>th) or (val<th) and (th<0)
    sigmax = np.max(signal)
    sigmin = np.min(signal)
    if exceeds(sigmax, threshold) or exceeds(sigmin, threshold):
        return True
    return False

def handle_spike(e):
    print "spike detected",str(e)
    fb.trigger_event('do_beep')


client.start_streaming()

events_handled = 0
lastidx=None

startidx=client.get_last_sample()
while events_handled < events_needed:
    if lastidx == client.get_last_sample():
        client.poll(lastidx, lastidx+1)
        lastidx = client.get_last_sample()
    else:
        lastidx = client.get_last_sample()
        
    data = client.get_data(lastidx-block_size, lastidx)

    event = check_threshold(data[:,0], threshold)
    wait+=1
    if event and (wait>=0):
        handle_spike(events_handled)
        wait=wait_blocks
        events_handled+=1
        
stopidx=client.get_last_sample()
#client.stop_streaming()