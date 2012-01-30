import numpy as np
import rdaclient as rc
import Gnuplot

#------------------------------------------------------------------------------ 

address = ('', 51244)
#address = ('192.168.2.1', 51244)

sampling_freq = 500 # hz
window = 500 # ms
channel = 1

real_width = True
delta = [0.1, 4]
alpha = [8., 12]
beta = [12., 30]
gamma = [25., 100]

#------------------------------------------------------------------------------ 

window = int(window / 1000.0 * sampling_freq)
sample_interval = 1.0 / sampling_freq

client = rc.Client(buffer_size=300000, buffer_window=window)
client.connect(address)
client.start_streaming()

g = Gnuplot.Gnuplot()
g('set yrange [0:100]')
#g('set yrange [-1:1]')
if real_width:
    g('set xrange [0:%s]' % np.max(gamma))
    g.xlabel('frequency, Hz')
else:
    g.xlabel('delta, alpha, beta, gamma')
    g('set xrange [0.5:4.5]')
    
g.ylabel('power')
g('set grid')

widths = np.array([delta[1] - delta[0],
                   alpha[1] - alpha[0],
                   beta[1] - beta[0],
                   gamma[1] - gamma[0]])

x = np.array([delta[0] + widths[0] / 2,
              alpha[0] + widths[1] / 2,
              beta[0] + widths[2] / 2,
              gamma[0] + widths[3] / 2])


def run_fft():
    lastidx = None
    while client.is_streaming:
        sig = client.poll(window)
                
        if sig is not None:
            sig = sig[:, channel]
            freq = np.fft.fftfreq(len(sig), sample_interval)
            spec = np.abs(np.fft.fft(sig)) ** 2
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
            
            np.reshape(loc_x, (-1, 1))
            np.reshape(bands, (-1, 1))
            np.reshape(loc_widths, (-1, 1))
            
            data = np.vstack((loc_x, bands, loc_widths)).T
            
            
            d = Gnuplot.Data(data, with_='boxes')
#            d = Gnuplot.Data(sig, with_='lines')
            g.plot(d)

run_fft()



