import lib.bcinetwork as bnet
import lib.bcixml as xml
import socket

class pyff_client():

    def connect(self):
        self.net = bnet.BciNetwork('', 12345)
    
    def trigger_event(self, name):
        sig = xml.BciSignal({'name':name}, None, xml.CONTROL_SIGNAL)
        self.net.send_signal(sig)
        
    def close(self):
        self.net.socket.close()
    