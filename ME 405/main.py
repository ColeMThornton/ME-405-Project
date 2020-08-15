# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:33:41 2020

@author: Katherine Hui
@author: Cole Thornton
"""

import pyb
from micropython import alloc_emergency_exception_buf
import gc

import cotask
import task_share

from MotorClass import MotorEncoder
from MotorClass import MotorCtl
from MotorClass import MotorDriver
from UltrasonicSourcedCode import HCSR04

alloc_emergency_exception_buf (1000)

# =============== CODE FOR SETUP OF INFRARED SENSOR PIN/TIMER =================
pinPA8 = pyb.Pin (pyb.Pin.board.PA8, pyb.Pin.ALT) 
tim1 = pyb.Timer (1, prescaler = 79, period = 0xFFFF) 
ch1 = tim1.channel (1, pyb.Timer.IC, polarity = pyb.Timer.BOTH, pin = pinPA8)
# =============================================================================
#
#
#
# ============================ QUEUES AND SHARES ==============================
q0 = task_share.Queue ('I', 68, thread_protect = False, overwrite = False,
                           name = "Queue_0")
IR_share = task_share.Share('B', thread_protect = True, name = 'IR_ON_OFF')


front_sensor_L = task_share.Share('B', thread_protect = True, 
                                  name = 'Left Front Sensor')
front_sensor_R = task_share.Share('B', thread_protect = True, 
                                  name = 'Right Front Sensor')

motor_state = task_share.Share('I', thread_protect = True, 
                               name = 'States of Motors')

front_pos_share = task_share.Share('I', thread_protect = True, 
                                   name = 'Front_Position')


opponent_found_1 = task_share.Share('B', thread_protect = True,
                                  name = 'Opponent There 1')
opponent_found_2 = task_share.Share('B', thread_protect = True,
                                  name = 'Opponent There 2')
proximity_alert_1 = task_share.Share('B', thread_protect = True,
                                   name = 'Opponent Very Close 1')
proximity_alert_2 = task_share.Share('B', thread_protect = True,
                                   name = 'Opponent Very Close 2')
opponent_set = task_share.Share('I', thread_protect = True, 
                                name = 'Opponent Setpoint')
last_motor_turn= task_share.Share('B', thread_protect = True,
                                  name = 'Last Motor Turn Direction')

left_turn_counter = task_share.Share('I', thread_protect = True,  name = 'LTurn_Timing')
right_turn_counter = task_share.Share('I', thread_protect = True,  name = 'RTurn_Timing')
left_turn_done = task_share.Share('B', thread_protect = True, name = 'LTurn_Bool')
right_turn_done = task_share.Share('B', thread_protect = True, name = 'RTurn_Bool')
backed_away = task_share.Share('B', thread_protect = True, name = 'Backup_Bool')
backup_counter = task_share.Share('B', thread_protect = True, name = 'Backup_Timer')

# =============================================================================
#
#
# ============================ MASTERMIND TASK ================================
def Mastermind():
    ''' @brief This task interprets the output from the infrared, ultrasonic 
    and line sensors to set the motor states accordingly. 
    @details This task is responsible to put the motors in the proper FORWARD,
    BACKWARD, LEFT_TURN, RIGHT_TURN, SCANNING, PUSHING, or STOPPED states.'''
    
   
    STOPPED = 0
    FORWARD = 1
    BACKWARD = 2
    LEFT_TURN = 3
    RIGHT_TURN = 4
    PUSHING = 5
    SCANNING = 6
    motor_state.put(STOPPED)
    IR_share.put(False)
    opponent_found_1.put(False)
    opponent_found_2.put(False)
    left_turn_done.put(True)
    right_turn_done.put(True)
    backed_away.put(True)
    last_motor_turn.put(1)

    while True:
        
        if IR_share.get() == False:
            motor_state.put(STOPPED)
    
        else:     
            if left_turn_done.get() == False:
                motor_state.put(LEFT_TURN)
                
            elif right_turn_done.get() == False:
                motor_state.put(RIGHT_TURN)
                
            elif backed_away.get() == False:
                motor_state.put(BACKWARD)
                
            elif front_sensor_L.get() == True and front_sensor_R.get() == True:
                motor_state.put(BACKWARD)
                backed_away.put(False)
            
            elif front_sensor_L.get() == True:
                motor_state.put(RIGHT_TURN)
                right_turn_done.put(False)
                
            elif front_sensor_R.get() == True:
                motor_state.put(LEFT_TURN)
                left_turn_done.put(False)
               
            elif opponent_found_1.get() == False and opponent_found_2.get() == False:
                motor_state.put(SCANNING)
                
            elif opponent_found_1.get() == True or opponent_found_2.get() == True:
                if proximity_alert_1.get() == True and proximity_alert_2.get() == True:
                        motor_state.put(PUSHING)
                else:
                    motor_state.put(FORWARD)
                    
        print(motor_state.get())     
            
        yield(1)
# =============================================================================
#
#
# ============================= LINE SENSOR TASKS =============================
def Left_Line():
    '''@brief This task senses if the left line sensor has seen a line or not. 
    @details This task interprets the analog signals from one line sensor in 
    the front on the left side, in order to determine if the bot has 
    read a line or not. '''
    
    FL_line_sensor = pyb.ADC('PB0')

    while True:
        line_pin_val_L = FL_line_sensor.read()
        if line_pin_val_L < 600:
            front_sensor_L.put(True)
            
        elif line_pin_val_L > 1000:
            front_sensor_L.put(False)

        yield(0)

def Right_Line():
    '''@brief This task senses if the right line sensor has seen a line or not. 
    @details This task interprets the analog signals from one line sensor
    in the front on the right side, in order to determine if the bot has 
    read a line or not. '''
        
    FR_line_sensor = pyb.ADC('PA4')
    
    while True:
        line_pin_val_R = FR_line_sensor.read()
        if line_pin_val_R < 600:
            front_sensor_R.put(True)
    
        elif line_pin_val_R > 1000:
            front_sensor_R.put(False)
        
        yield(0)
# =============================================================================
#
#
# ======================= INFRARED SENSOR TASK ================================

def Infrared_Task():
    '''@brief This function deciphers a packet of information sent by an infrared
    remote and decodes repeat signals. 
    
    @details This function stores time stamps from a timer interrupt triggering
    on rising and falling edges. It calculates the difference between time
    stamps to determine the logic high or low of the signal. Once a full packet
    has been processed, the value of the signal corresponding to the button
    pressed is calculated. '''

    full_packet = False        # flag for if a full packet has been received
    my_int = 0                 # decimal value of infrared packet logic
    time_pulse = []            # list for time stamp values from interrupt
    logicals = []              # list for logical values of infrared packet
    
    pinPA8 = pyb.Pin (pyb.Pin.board.PA8, pyb.Pin.ALT)
    tim1 = pyb.Timer(1, prescaler = 79, period = 0xFFFF)
    ch1 = tim1.channel(1, pyb.Timer.IC, polarity = pyb.Timer.BOTH, pin = pinPA8)

    while True: 
        
        # The channel 1 callback generates the interrupt and stores timestamp
        # values of rising and falling edges in the queue q0. The values in
        # q0 are appended to a list 
        ch1.callback(interrupt)
        
        if q0.empty() == True:
            pass
        
        else:
            
            time_pulse.append(q0.get())
            
            # The function logic_process processes the time_pulse data and
            # determines the logic value of the time difference
            
            logic_process(time_pulse, logicals)
            
            # When the length of logicals reaches 32, then a full packet of 
            # data has been processed and a valid button has been pressed (not 
            # repeat code). The full_packet flag is set to True, and the data 
            # can be parsed and converted into binary. If not 32, the program 
            # loops back to the interrupt and waits for more time stamps to 
            # fill logicals.
           
            if len(logicals) == 32:       	
                full_packet = True
            else:
            	full_packet = False	
    
            # If the length of logicals is 32, then the data can be parsed. 
            # Each value of logicals is sorted through and converted into an 
            # integer using the bitwise ior (|=) operator. 
            # Then, the address byte, its inverse, the command byte, and its 
            # inverse are converted from the main integer (32-bit) into their 
            # own integers (8-bit).
            
            if full_packet == True:
                for n in range(len(logicals)):
                    my_int |= logicals[n] << n
                
                address_byte = my_int & 0xFF
                address_byte_inverse = (my_int >> 8) & 0xFF
                command_byte = (my_int >> 16) & 0xFF
                command_byte_inverse = (my_int >> 24) & 0xFF

                if command_byte == 12:
                    IR_share.put(True)
                
                else:
                    IR_share.put(False)
                    
                # The time pulse list is cleared, and then a 1 is appended to 
                # the first spot to have the next value appended be a rising 
                # edge. The logicals list is cleared, my_int is set back to 0, 
                # and the full_packet flag is set back to False.
                
                time_pulse = []
                time_pulse.append(1)
                logicals = []
                my_int = 0
                full_packet = False
        
        yield(0)


# ======================= INFRARED SENSOR FUNCTIONS ===========================
def interrupt (timer):
    ''' This function (in an interrupt) stores rising/falling edge time stamps 
    in a queue. '''

    q0.put(ch1.capture(), in_ISR = True)

def logic_process(time_pulse, logicals):
    ''' This function deciphers the pulses received from the infrared
	interrupt and decodes if it is logic high or low or if it should be 
    ignored.
    
    @param time_pulse List of time stamp values from the interrupt and timer
           trigger.
    @param logicals List of logical high or low values from infrared signal.
    
    '''	   
    
    # First, check if the length of the list containing the time stamps is 3.
    # if not, then pass. If so, then take the difference between the 2nd and 
    # 3rd time stamps in order to find the duration of the pulse. If the
    # duration between the time stamps is negative (overflow occurred) it
    # must be offset by 65535. The time difference between each pulse is tested
    # between certain ranges to determine if it is logic high (1), logic low (0)
    # or should be ignored (oustide of both ranges). The logic value is
    # appended to a list containing all of the logical values for the data
    # packet. 
    
    if len(time_pulse) < 3:
        pass
    
    else:
        time_diff = time_pulse[2] - time_pulse[1]
        
        if time_diff < 0 :
        	time_diff += 65535
        
        if 475 <= time_diff <= 700:
        	logicals.append(0)
        
        elif 1550 <= time_diff <= 1800:
        	logicals.append(1)

        else:
        	pass
        
        # The 2nd and 3rd time stamp values are deleted after finding the 
        # difference in order to make new space for the upcoming values. The
        # function call returns the list of logical values (but isn't used).
        
        del time_pulse[1]
        del time_pulse[1]
        return(logicals)
# =============================================================================
#
#
# ========================== ULTRASONIC TASK ==================================
def Ultrasonic_Task():
    '''@brief This task alternates between reading the left and right ultrasonic 
    sensors at the front of the Soomba. 
    
    @details The signal read back by the sensor is converted into a distance in 
    inches and processed in order to determine if the opponent is in front or 
    at a very close proximity. '''
    
    Ultra_1 = 1
    Ultra_2 = 2
    L_Ultra = HCSR04('PA5', 'PA6')
    R_Ultra = HCSR04('PB8', 'PB9')
    state = Ultra_2
    
    while True:
        if state == Ultra_1:
            L_Ultra._send_pulse_and_wait()
            distance_1 = L_Ultra.distance_inch()

            if distance_1 < 6:
                opponent_found_1.put(True)
                proximity_alert_1.put(True)
            
            elif 6 < distance_1 < 30:
                opponent_found_1.put(True)
                ticks_L = 750*int(distance_1)
                opponent_set.put(ticks_L)
            
            else:
                opponent_found_1.put(False)
                proximity_alert_1.put(False)
            
            state = Ultra_2
                
        if state == Ultra_2:
            R_Ultra._send_pulse_and_wait()
            distance_2 = R_Ultra.distance_inch()

            if 0 < distance_2 < 6:
                proximity_alert_2.put(True)
                opponent_found_2.put(True)
                
            elif 6 < distance_2 < 30:
                opponent_found_2.put(True)
                ticks_R = 750*int(distance_2)
                opponent_set.put(ticks_R)

            else:
                opponent_found_2.put(False)
                proximity_alert_2.put(False)
            
            state = Ultra_1
        
        yield(state)
# =============================================================================
#
#        
# =========================== ENCODER TASKS ===================================   
        
def Encoder_Task():
   ''' @brief This task reads the encoder on the front of the robot and zeros the
   encoder when the robot is not in motion. 
   
   @details When in the forward state, the encoder position is put into a 
   share; otherwise, it is zeroed. '''
   
   enc = MotorEncoder('PB6','PB7',4) 
   enc.zero()
   
   while True:
       if IR_share.get() == False:
           enc.zero()
           
       else:
           if motor_state.get() == 1:
               current_front_pos = enc.read()
               front_pos_share.put(current_front_pos)
           else:
               enc.zero()
        
       yield(0)

# ============================= MOTOR TASKS ===================================
def Motors_Task():
    ''' @brief This task sets the motor duty cycles with respect to the motor state
    that is set. 
    
    @details The motor has seven states: Stopped, Forward, Backward,
    Left Turn, Right Turn, Pushing, and Scanning. Before the infrared sensor
    triggers, the default state is Stopped. With no sensor readings, the default
    state is Scanning. 
    '''
    
    driver_1 = MotorDriver('PA10','PB4','PB5', 3)
    driver_2 = MotorDriver('PC1','PA0','PA1', 5)             
    ctrl_1 = MotorCtl()
    driver_1.set_duty_cycle(0)
    driver_2.set_duty_cycle(0)
    
    while True:
        # state for stopped
        if motor_state.get() == 0:
            driver_1.set_duty_cycle(0)
            driver_2.set_duty_cycle(0)

        # state for forward movement
        elif motor_state.get() == 1:
            dty = ctrl_1.control_loop(front_pos_share.get(), opponent_set.get())
            dty = abs(dty)
            driver_1.set_duty_cycle(dty)
            driver_2.set_duty_cycle(-dty)

        # state for backward movement        
        elif motor_state.get() == 2:
            if backup_counter.get() == 0:
                driver_1.set_duty_cycle(0)
                driver_2.set_duty_cycle(0)
                
            driver_1.set_duty_cycle(-40)
            driver_2.set_duty_cycle(40)
            count = backup_counter.get()
            count += 1
            backup_counter.put(count)
            
            if count == 80:
                backup_counter.put(0)
                backed_away.put(True)

        # state for left turn movement           
        elif motor_state.get() == 3:
            if left_turn_counter.get() <= 25:
                driver_1.set_duty_cycle(0)
                driver_2.set_duty_cycle(0)
                
            elif 25 < left_turn_counter.get() <= 150:
                driver_1.set_duty_cycle(-30)
                driver_2.set_duty_cycle(30)
                
            elif 150 < left_turn_counter.get() < 275:
                driver_1.set_duty_cycle(-60)
                driver_2.set_duty_cycle(-60)
            
            count = left_turn_counter.get()
            count += 1         
            left_turn_counter.put(count)
            
            if count == 250:
                left_turn_done.put(True)
                left_turn_counter.put(0)
                last_motor_turn.put(1)

        # state for right turn movement            
        elif motor_state.get() == 4:
            if right_turn_counter.get() == 0:
                driver_1.set_duty_cycle(0)
                driver_2.set_duty_cycle(0)
                
            elif 25 < right_turn_counter.get() <= 150:
                driver_1.set_duty_cycle(-30)
                driver_2.set_duty_cycle(30)
                
            elif 150 < right_turn_counter.get() < 275:
                driver_1.set_duty_cycle(60)
                driver_2.set_duty_cycle(60)
            
            count = right_turn_counter.get()
            count += 1         
            right_turn_counter.put(count)
            
            if count == 250:
                right_turn_done.put(True)
                right_turn_counter.put(0)
                last_motor_turn.put(0)

        # state for pushing movement           
        elif motor_state.get() == 5:
            driver_1.set_duty_cycle(90)
            driver_2.set_duty_cycle(-90)

        # state for scanning movement     
        elif motor_state.get() == 6:
                if last_motor_turn.get() == 1:
                    driver_1.set_duty_cycle(-60)
                    driver_2.set_duty_cycle(-60)
                
                elif last_motor_turn.get() == 0:
                    driver_1.set_duty_cycle(60)
                    driver_2.set_duty_cycle(60)
                
        
        yield(0)
# =============================================================================            

           
# =============================================================================

if __name__ == "__main__":

    print ('\033[2JTesting scheduler in cotask.py\n')

    # Create a share and some queues to test diagnostic printouts
    q0 = task_share.Queue ('I', 68, thread_protect = False, overwrite = False,
                           name = "Queue_0")
    front_sensor_L = task_share.Share('B', thread_protect = True, name = 'Left Front Sensor')
    front_sensor_R = task_share.Share('B', thread_protect = True, name = 'Right Front Sensor')
    motor_state = task_share.Share('I', thread_protect = True, name = 'States of Motors')
    IR_share = task_share.Share('B', thread_protect = True, name = 'IR_ON_OFF')
    
    front_pos_share = task_share.Share('I', thread_protect = True, name = 'Front_Position')
    back_pos_share = task_share.Share('I', thread_protect = True, name = 'Back_Position')


    # Create the tasks. If trace is enabled for any task, memory will be
    # allocated for state transition tracing, and the application will run out
    # of memory after a while and quit. Therefore, use tracing only for 
    # debugging and set trace to False when it's not needed
    
    task1 = cotask.Task (Mastermind, name = 'Mastermind_Task', priority = 7,
                         period = 20, profile = True, trace =  False)
    task2 = cotask.Task (Motors_Task, name = 'Motors_Task', priority = 6, 
                         period = 15, profile = True, trace = False)
    task3 = cotask.Task (Encoder_Task, name = 'Front_Encoder_Task', 
                         priority = 3, period = 10, profile = True, trace = False)
    task4 = cotask.Task (Infrared_Task, name = 'Infrared_Sensor_Task', 
                         priority = 5, period = 10, profile = True, trace = False)
    task5 = cotask.Task (Left_Line, name = 'Left_Line_Sensor_Task', priority = 4,
                         period = 10, profile = True, trace = False)
    task6 = cotask.Task (Right_Line, name = 'Right_Line_Sensor_Task', priority = 4,
                         period = 10, profile = True, trace = False)
    task7 = cotask.Task (Ultrasonic_Task, name = 'Ultrasonic_Sensor_Task', 
                         priority = 4, period =  10, profile = True, trace = False)
   
    cotask.task_list.append (task1)
    cotask.task_list.append (task2)
    cotask.task_list.append (task3)
    cotask.task_list.append (task4)
    cotask.task_list.append (task5)
    cotask.task_list.append (task6)
    cotask.task_list.append (task7)


    # Run the memory garbage collector to ensure memory is as defragmented as
    # possible before the real-time scheduler is started
    gc.collect ()

    # Run the scheduler with the chosen scheduling algorithm. Quit if any 
    # character is sent through the serial port
    vcp = pyb.USB_VCP ()
    while not vcp.any ():
        cotask.task_list.pri_sched ()

    # Empty the comm port buffer of the character(s) just pressed
    vcp.read ()

    # Print a table of task data and a table of shared information data
    print ('\n' + str (cotask.task_list) + '\n')
    print (task_share.show_all ())
    print ('\r\n')          
    
    