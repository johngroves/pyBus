#!/usr/bin/python

import os, sys, time, signal, json, logging, traceback
import threading

import pyBus_module_display as pB_display # Only events can manipulate the display stack
import pyBus_module_audio as pB_audio # Add the audio module as it will only be manipulated from here in pyBus

# This module will read a packet, match it against the json object 'DIRECTIVES' below. 
# The packet is checked by matching the source value in packet (i.e. where the packet came from) to a key in the object if possible
# Then matching the Destination if possible
# The joining the 'data' component of the packet and matching that if possible.
# The resulting value will be the name of a function to pass the packet to for processing of sorts.

# THE MAJOR DIFFRENCE BETWEEN THIS DRIVER AND EVENT DRIVER:
# This one should manipulate the state data object and use that with
# a ticking thread to figure out what to do. So tick every .5 sec or 
# so and perform an action depending on the state data like skipping
# back or forward.

#####################################
# GLOBALS
#####################################
WRITER = None
STATE_DATA = {}
FUNC_STACK = {}
TICK = 1 # sleep interval in seconds used between iBUS reads
TOCK = True

#####################################
# FUNCTIONS
#####################################
# Set the WRITER object (the iBus interface class) to an instance passed in from the CORE module
def init(writer):
  global WRITER
  logging.info("Initializing the iBus interface for tickDriver")
  WRITER = writer

def shutDown():
  global WRITER
  logging.info("Dereferencing iBus interface")
  WRITER = None

def enableFunc(funcName, interval, count=0):
  global FUNC_STACK

  # Cancel Thread if it already exists.
  if FUNC_STACK.get(funcName) and FUNC_STACK.get(funcName).get("THREAD"):
    FUNC_STACK[funcName]["THREAD"].cancel()

  # Dont worry about checking if a function is already enabled, as the thread would have died. Rather than updating the spec, just run a new thread.
  if getattr(sys.modules[__name__], funcName):
    UUID = os.urandom(32) # this is a fantastic idea if I do say so myself!
    FUNC_STACK[funcName] = {
      "COUNT": count,
      "THREAD": threading.Timer(
        interval,
        do_every, [funcName]
      )
    }
    logging.debug("Enabling New Thread:\n%s" % FUNC_STACK[funcName])
    do_every(funcName) # Begins loop of function calls, each one occurring as close to the interval as possible.
  else:
    logging.warning("No function found (%s)" % funcName)

def disableFunc(funcName):
  global FUNC_STACK
  if funcName in FUNC_STACK.keys():
    thread = FUNC_STACK[funcName].get("THREAD")
    if thread: thread.cancel()
    del FUNC_STACK[funcName]

def disableAllFunc():
  global FUNC_STACK
  for funcName in FUNC_STACK:
    thread = FUNC_STACK[funcName].get("THREAD")
    if thread: thread.cancel()
  FUNC_STACK = {}

#------------------------------------
# THREAD FOR TICKING AND CHECKING EVENTS
#------------------------------------
def do_every(funcName):
  global FUNC_STACK
  funcSpec = FUNC_STACK.get(funcName, None)
  worker_func = getattr(sys.modules[__name__], funcName)
  if funcSpec and worker_func:
    count = funcSpec["COUNT"]
    if count != 1:
      FUNC_STACK[funcName]["COUNT"] = count - 1
      FUNC_STACK[funcName]["THREAD"].start()
    worker_func()
#------------------------------------

#####################################
# Tick Functions
#####################################
def scanForward():
  pB_audio.seek(5)

def scanBackward():
  pB_audio.seek(-5)  

def pollResponse():
  WRITER.writeBusPacket('18', 'FF', ['02','00'])