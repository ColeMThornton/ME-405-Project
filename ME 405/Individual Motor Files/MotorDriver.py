# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 13:55:52 2020

@author: Cole Thornton and Katherine Hui
"""

class MotorDriver:
    ''' This class implements a motor driver for the ME405 board. '''
    
    def __init__ (self):
        ''' Creates a motor driver by initializing GPIO
        pins and turning the motor off for safety. '''
        import pyb
        print ('Motor driver created.')
        
        # Initalize pins
        self.pinPA10=pyb.Pin (pyb.Pin.board.PA10, pyb.Pin.OUT_PP) 
        self.pinPA10.low () 
        self.pinPB4=pyb.Pin (pyb.Pin.board.PB4, pyb.Pin.OUT_PP) 
        self.pinPB4.low () 
        self.pinPB5=pyb.Pin (pyb.Pin.board.PB5, pyb.Pin.OUT_PP) 
        self.pinPB5.low () 
        # Generate PWM signal using timer
        self.tim3 = pyb.Timer (3, freq=20000) 
        self.ch2 = self.tim3.channel (2, pyb.Timer.PWM, pin=self.pinPB5) 
        self.ch1 = self.tim3.channel (1, pyb.Timer.PWM, pin=self.pinPB4) #
        
    def set_duty_cycle (self, level):
        ''' This method sets the duty cycle to be sent to the motor to the 
        given level. Positive valuse cause torque in one direction, negative 
        values in the opposite direction.
        @param level A signed integer holding the duty cycle of the voltage
        sent to the motor '''
        self.pinPA10.high () #
        if level >= 0: #Postive duty cycle, motor turns counterclockwise
            self.ch1.pulse_width_percent (0)
            self.ch2.pulse_width_percent (level)
        else: # Negative duty cycle, motor turns clockwise
            self.ch2.pulse_width_percent (0)
            self.ch1.pulse_width_percent (abs(level))


