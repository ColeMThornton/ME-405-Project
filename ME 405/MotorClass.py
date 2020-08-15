# -*- coding: utf-8 -*-
"""
Created on Sat Feb 22 19:45:08 2020

@author: Katherine Hui
@author: Cole Thornton
"""
class MotorDriver:
    ''' This class implements a motor driver. '''
    
    def __init__ (self, input_pin, ch1_pin, ch2_pin, timer):
        ''' Creates a motor driver by initializing GPIO
        pins and turning the motor off for safety.
        @param input_pin The pin corresponding to the input power for the driver.
        @param pin_1 The pin corresponding to the positive PWM channel.
        @param pin_2 The pin corresponding to the negative PWM channel.
        @param timer The number of the timer for the specified pins. 
        '''
        
        import pyb
        self.input_pin = input_pin
        self.ch1_pin = ch1_pin
        self.ch2_pin = ch2_pin
        self.timer = timer
        
        # Initalize pins
        self.input_pin = pyb.Pin(self.input_pin, pyb.Pin.OUT_PP)
        self.ch1_pin = pyb.Pin (self.ch1_pin, pyb.Pin.OUT_PP)
        self.ch2_pin = pyb.Pin (self.ch2_pin, pyb.Pin.OUT_PP)
        
        self.input_pin.low()
        self.ch1_pin.low()
        self.ch2_pin.low()

        # Generate PWM signal using timer
        self.timer = pyb.Timer(self.timer, freq = 20000)
        self.ch1 = self.timer.channel (1, pyb.Timer.PWM, pin=self.ch1_pin)
        self.ch2 = self.timer.channel (2, pyb.Timer.PWM, pin=self.ch2_pin) 

        
    def set_duty_cycle (self, level):
        ''' This method sets the duty cycle to be sent to the motor to the 
        given level. Positive valuse cause torque in one direction, negative 
        values in the opposite direction.
        @param level A signed integer holding the duty cycle of the voltage
        sent to the motor '''
        
        # Set input pin to high
        self.input_pin.high ()
        
        # Postive duty cycle, motor turns clockwise
        if level >= 0: 
            self.ch1.pulse_width_percent (0)
            self.ch2.pulse_width_percent (level)
            
        # Negative duty cycle, motor turns counterclockwise
        else: 
            self.ch2.pulse_width_percent (0)
            self.ch1.pulse_width_percent (abs(level))

class MotorEncoder:
    ''' This class utilizes the motor's built-in encoder to read back position.
    '''
    
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
    
    def read(self):
        '''This method reads the current position of either motor and accounts
        for overflow and underflow. '''
        
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
        ''' This method resets the motor position back to zero. '''
        
        self.timer.counter(0)                  # set encoder reading to 0
        self.previous_pos = 0
        self.motor_pos = 0
        return self.motor_pos

class MotorCtl:
    ''' This class implements a closed-loop control system for the motor with
    a setpoint position value and set proportional gain. '''
    
    def __init__(self, init_K_P=0.2, init_set=0):
        ''' This initializes the values of K_P and setpoint for a motor.
        @param init_K_P The inital proportional gain value.
        @param init_set The inintial setpoint position value. '''
        
        self.K_P = init_K_P
        self.setpoint = init_set

        
    def control_loop(self, position, setpoint):
        ''' This method calculates the error in position between a setpoint
        and current value and multiplies it by proportional gain.
        @param position The current position of the motor.
        @param setpoint The desired position of the motor. '''
        
        self.position = position
        self.setpoint = setpoint
        self.error = self.setpoint - self.position
        self.error = self.error*self.K_P
        return self.error
    
    def set_setpoint(self, setpoint):
        ''' This method changes the setpoint position value.
        @param setpoint The new desired position of the motor. '''
        
        self.setpoint = setpoint
        return self.setpoint
    
    def set_K_P(self, K_P):
        ''' This method changes the proportional gain value. 
        @param K_P The new proportional gain value. '''
        
        self.K_P = K_P
        return self.K_P
