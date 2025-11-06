from Fluidics.Valves.Valve import *
import time
class ViciValve(Valve):
    """Vici valve implementation using serial communication.
    
    Controls Vici multi-position valves via serial commands. Supports
    port selection and status inquiry.
    
    Attributes:
        com_port (str): Serial COM port for valve controller.
        serial (serial.Serial): Serial connection to valve controller.
        acknowledge (str): Acknowledge message pattern.
        carriage_return (bytes): Carriage return byte sequence.
        negative_acknowledge (str): Negative acknowledge message.
        read_length (int): Maximum read length for serial responses.
        char_offset (int): Character offset for valve ID parsing.
    """
    
    def __init__(self, com_port, gui=False):
        """Initialize ViciValve with serial connection.
        
        Args:
            com_port (str): Serial COM port (e.g., 'COM6').
            gui (bool): Whether GUI mode is enabled. If True, skips serial connection.
                Defaults to False.
        """
        super().__init__()
        self.com_port = com_port # The serial port of the valve controller on the computer
        self.current_port = {} # A dictionary for storing the currently selected port of each vicivalve.
        
        if not gui:
            self.serial = serial.Serial(port = self.com_port, 
                                    baudrate = 9600, 
                                    bytesize = serial.EIGHTBITS, #8 bits
                                    parity = serial.PARITY_NONE, 
                                    stopbits = serial.STOPBITS_ONE, 
                                    timeout = 0.1)
        self.acknowledge = " ID = "
        self.carriage_return = bytes("\r", 'utf-8') # All serial messages from Vici valve end with a utf-8 encoded carriage return.
        self.negative_acknowledge = "" # The message from the Vici valve when it cannot respond properly.
        self.read_length = 64
        self.char_offset = 97

    def set_port(self, valve_ID, port_ID):
        """Select port on specified Vici valve.
        
        Sends formatted serial command to valve and waits for completion.
        Updates current_port dictionary.
        
        Args:
            valve_ID (int): Valve identifier (0-indexed).
            port_ID (int): Port number to select (0-indexed, converted to 1-indexed).
        """
        # Send a formated serial message readable by Vici Valve to select port with port_ID on the valve with valve_ID
        valve_ID = str(valve_ID)
        port_ID = str(int(port_ID)+1)
        message = valve_ID + "GO" + port_ID + "\r"
        self.write(message)
        time.sleep(1)
        # Update the current_port dictionary
        self.current_port[valve_ID] = self.get_port(valve_ID)

    def get_port(self, valve_ID):
        """Get currently selected port for specified Vici valve.
        
        Sends inquiry command and parses response.
        
        Args:
            valve_ID (int): Valve identifier.
        
        Returns:
            str: Currently selected port number, or None if inquiry fails.
        """
        message = "CP\r" # This is the serial message for Vici valve to return the current port.
        response = self.inquireAndRespond(valve_ID, message)
        if response[0] == "Negative Acknowledge":
            self.update_user("Move failed: " + str(response))
        if response[1]:
            return response[3].split(' ')[-1]
            
    def read(self):
        """Read serial message from Vici valve.
        
        Reads response and extracts content before carriage return marker.
        
        Returns:
            bytes: Response content before carriage return.
        """
        response = self.serial.read(self.read_length).split(self.carriage_return)[0]
        # if self.verbose:
            # self.update_user "Received: " + str((response, ""))
        return response
        
    def write(self, message):
        """Write serial message to Vici valve.
        
        Encodes message as UTF-8 and sends to valve controller.
        
        Args:
            message (str): Message string to send.
        """
        message = bytes(message, 'utf-8')
        self.serial.write(message)

    def inquireAndRespond(self, valve_ID, message, dictionary={}, default="Unknown"):
        """Send inquiry message to valve and parse response.
        
        Sends message to specified valve and interprets response based on
        provided dictionary mapping or default response type.
        
        Args:
            valve_ID (int): Valve identifier.
            message (str): Inquiry message to send.
            dictionary (dict, optional): Dictionary mapping response content to response type.
                Defaults to {}.
            default (str, optional): Default response type if not in dictionary.
                Defaults to "Unknown".
        
        Returns:
            tuple: (response_type, success, response_content) where:
                - response_type (str): Type of response ('Acknowledge', 'Negative Acknowledge', etc.)
                - success (bool): Whether response indicates success
                - response_content (str): Raw response content
        """
        # Send message and read response
        self.write(valve_ID + message)
        response = str(self.read())
        if len(response)>0:
            # Strip off valve id
            response = response[2:]
                
        # The case when the Vici Valve cannot respond
        if response == self.negative_acknowledge:
            return ("No Response", False, response)

        # The case when the Vici Valve responds 'Bad command'
        if 'Bad command' in response:
            # Parse provided dictionary with response
            return ("Negative Acknowledge", False, response)

        # If user provide a dictionary, map the content of the response to the corresponding type of the response.
        try:
            return_value = dictionary.get(response, default)
            if return_value == default:
                return (default, False, response)
            else:
                return (return_value, True, response)
        except:
        # Otherwise, use "Acknowledge" as the type of the response.
            return ("Acknowledge", True, response)



    


