"""
OSC Bridge for communicating with SuperCollider.
Sends parameter updates from Python to SuperCollider via OSC.
"""

from pythonosc import udp_client
import time


class OSCBridge:
    def __init__(self, ip="127.0.0.1", port=57120):
        """
        Initialize OSC client.
        
        Args:
            ip: SuperCollider server IP (default: localhost)
            port: SuperCollider server port (default: 57120)
        """
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.connected = False
        
    def connect(self):
        """Test connection to SuperCollider."""
        try:
            self.client.send_message("/status", [])
            self.connected = True
            print(f"✓ Connected to SuperCollider at 127.0.0.1:57120")
            return True
        except Exception as e:
            print(f"✗ Could not connect to SuperCollider: {e}")
            self.connected = False
            return False
            
    def send_parameter(self, param_name, value):
        """
        Send a single parameter update.
        
        Args:
            param_name: Name of the parameter (e.g., 'gravity')
            value: Parameter value (0.0 - 1.0)
        """
        osc_address = f"/noise/{param_name}"
        try:
            self.client.send_message(osc_address, float(value))
        except Exception as e:
            print(f"Error sending {param_name}: {e}")
            
    def send_all_parameters(self, params_dict):
        """
        Send all parameters at once.
        
        Args:
            params_dict: Dictionary of parameter names and values
        """
        for param_name, value in params_dict.items():
            self.send_parameter(param_name, value)


if __name__ == "__main__":
    """Test the OSC bridge."""
    print("Testing OSC Bridge...")
    print("Make sure SuperCollider is running!")
    
    bridge = OSCBridge()
    
    if bridge.connect():
        print("\nSending test messages...")
        
        # Send some test values
        bridge.send_parameter("gravity", 0.5)
        time.sleep(0.1)
        bridge.send_parameter("density", 0.7)
        time.sleep(0.1)
        bridge.send_parameter("filter_cutoff", 0.3)
        time.sleep(0.1)
        bridge.send_parameter("amplitude", 0.6)
        
        print("✓ Test messages sent")
    else:
        print("✗ Connection failed")
