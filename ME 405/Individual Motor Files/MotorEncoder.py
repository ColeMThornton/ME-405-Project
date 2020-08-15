""" The following code is used to set up the encoder for a DC motor and
readback the position.

Author: Cole Thornton & Katherine Hui

Date started: 1/16/20

Last Edit: 1/26/20 

"""

class MotorEncoder:

    def __init__(self, pin_1, pin_2, timer):
        ''' Creates a motor encoder by initializing GPIO pins and initializes 
        the timer and its channels, 1 and 2, by using the two pins for the 
        encoder and the timer number as inputs for the class.
       
        @param pin_1 The pin corresponding to the A encoder channel.
        @param pin_2 The pin corresponding to the B encoder channel.
        @param timer The number of the timer for the specified pins. 
        '''
        import pyb
        self.pin_1 = pin_1
        self.pin_2 = pin_2
        self.timer = timer
        self.pin_1 = pyb.Pin(self.pin_1, pyb.Pin.ALT)
        self.pin_2 = pyb.Pin (self.pin_2, pyb.Pin.ALT)
        self.timer = pyb.Timer(self.timer, period = 0xFFFF, prescaler=0)
        self.ch1 = self.timer.channel(1, pyb.Timer.ENC_A, pin=self.pin_1)
        self.ch2 = self.timer.channel(2, pyb.Timer.ENC_B, pin=self.pin_2)
        self.previous_pos = 0                 # set previous position to 0
        self.motor_pos = 0                    # set motor position to 0
        print('The encoder is set up.')
    
    def read(self):
        '''This reads the current position of either motor and accounts for
        overflow and underflow. '''
        
        self.current_pos = self.timer.counter()
        self.offset = self.current_pos - self.previous_pos
        self.previous_pos = self.current_pos
        if self.offset < -32768:                # for overflow of values
            self.offset = self.offset + 65536
        elif self.offset > 32767:               # for underflow of values 
            self.offset = self.offset - 65536
        self.motor_pos += self.offset           # add offset to motor position
        return self.motor_pos
      
    def zero(self):
        ''' This resets the motor position back to zero. '''
        self.timer.counter(0)                  # set encoder reading to 0
        self.previous_pos = 0
        self.motor_pos = 0
        return self.motor_pos