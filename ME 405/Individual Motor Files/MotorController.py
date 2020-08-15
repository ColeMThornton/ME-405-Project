# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 12:44:42 2020

@author: Cole Thornton
@author: Katherine Hui

Created 1/30/20

"""

class MotorCtl:

    def __init__(self, init_K_P=0, init_set=0):
        ''' This initializes the values of K_P and setpoint for a motor. '''
        self.K_P = init_K_P
        self.setpoint = init_set
        print('Control loop ready.')
        
    def control_loop(self, position, setpoint):
        ''' This method calculates the error in position between a setpoint
        and current value and multiplies it by proportional gain.'''
        self.position = position
        self.setpoint = setpoint
        self.error = self.setpoint - self.position
        self.error = self.error*self.K_P
        return self.error
    
    def set_setpoint(self, setpoint):
        ''' This method changes the setpoint position value. '''
        self.setpoint = setpoint
        return self.setpoint
    def set_K_P(self, K_P):
        ''' This method changes the proportional gain value. '''
        self.K_P = K_P
        return self.K_P