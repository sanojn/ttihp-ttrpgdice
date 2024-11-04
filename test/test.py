# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.triggers import RisingEdge
from cocotb.triggers import Trigger
from cocotb.triggers import Edge
from cocotb.triggers import Timer

def hex(n): # Return a binary octet with 2 BCD digits
  return ((n%100)//10)*16 + n%10;

def internalDigits(dut): # Return the two internal digit counters as an octet
  return dut.digit10.value*16 + dut.digit1.value

def releaseButtons(dut):
    dut.btn4.value = 0;
    dut.btn6.value = 0;
    dut.btn8.value = 0;
    dut.btn10.value = 0;
    dut.btn12.value = 0;
    dut.btn20.value = 0;
    dut.btn100.value = 0;

async def testCycle(dut,period):
    await ClockCycles(dut.clk, 1, False) # allow for synch delay
    # allow input to be deglitched
    while (dut.user_project.tick.value==0):
      await ClockCycles(dut.clk,1,False)
    await ClockCycles(dut.clk,1,False)
    while (dut.user_project.tick.value==0):
      await ClockCycles(dut.clk,1,False)
    await ClockCycles(dut.clk, 1, False) # Let the debounce FSM see the tick
    # Now the counter should be rolling
    # Wait until it's 1 to simplify tests
    if (internalDigits(dut)!=hex(1)):
      for i in range(0,period):
        await ClockCycles(dut.clk, 1, False)
        if (internalDigits(dut)==hex(1)):
          break;
    # Check one period
    for i in range(period,0,-1):
      await ClockCycles(dut.clk, 1, False)
      assert internalDigits(dut) == hex(i)
    # Check one more period
    for i in range(period,0,-1):
      await ClockCycles(dut.clk, 1, False)
      assert internalDigits(dut) == hex(i)
    # Multiple cycles
    await ClockCycles(dut.clk, 3*period, False)
    assert internalDigits(dut) == hex(1)
    # Run the last part only if we're actually pressing a button
    if (period!=1):
      # Release button and verify that counting stops
      releaseButtons(dut);
      await ClockCycles(dut.clk,1,False) # Allow for synch delay
      assert internalDigits(dut) == hex(period) # Counter should have rolled over 
      await ClockCycles(dut.clk,1,False)
      assert internalDigits(dut) == hex(period-1) # The debouncer changes state as we roll down once more
      await ClockCycles(dut.clk,1,False)
      assert internalDigits(dut) == hex(period-1) # The counter should have stopped now
      await RisingEdge(dut.user_project.tick)  # Wait a while so the debouncer knows the button is released
      assert internalDigits(dut) == hex(period-1) # Verify that the counter hasn't moved
      await ClockCycles(dut.clk, 7, False)
      assert internalDigits(dut) == hex(period-1) # Verify that the counter hasn't moved

def noDigitsShown(dut): # Check if the 'common' signal of both displays are off
  return ( not dut.digit1_active.value and not dut.digit10_active.value )

async def checkDigitsShown(dut):
   while (dut.anyButtonPressed.value==1): # some button is pressed, We shouldn't see any digits
     await Timer(1, units='ms');
     if (dut.anyButtonPressed.value==1): # Check that button wasn't released before looking at the digit
       assert noDigitsShown(dut);
   while (not dut.anyButtonPressed.value==1): # no button is pressed, something should be shown on the display
     await Timer(1, units='ms');
     if (not dut.anyButtonPressed.value==1):
         if noDigitsShown(dut):  # if no digit is shown, maybe this a blanked digit10. Wait for the other digit
             await Edge(dut.clk);
             await Timer(1, units='us');
             assert not noDigitsShown(dut);

async def checkSegmentOutputs(dut):
  await Edge(dut.shownDigit);
  assert dut.shownDigit.value != 14;
  if (dut.digit1_active.value):
    assert dut.shownDigit.value == dut.digit1.value;
  elif (dut.digit10_active.value):
    assert dut.shownDigit.value == dut.digit10.value;
  else:
    assert dut.digit10.value==0;
  

async def testAllButtons(dut):
  dut._log.info("Testing no button")
  releaseButtons(dut)
  await testCycle(dut,1)
  dut._log.info("Testing btn4")
  dut.btn4.value = 1
  await testCycle(dut,4)
  dut._log.info("Testing btn6")
  dut.btn6.value = 1
  await testCycle(dut,6)
  dut._log.info("Testing btn8")
  dut.btn8.value = 1
  await testCycle(dut,8)
  dut._log.info("Testing btn10")
  dut.btn10.value = 1
  await testCycle(dut,10)
  dut._log.info("Testing btn12")
  dut.btn12.value = 1
  await testCycle(dut,12)
  dut._log.info("Testing btn20")
  dut.btn20.value = 1
  await testCycle(dut,20)
  dut._log.info("Testing btn100")
  dut.btn100.value = 1
  await testCycle(dut,100)

async def reset(dut):
  dut._log.info("Reset")
  dut.ena.value = 1
  dut.rst_n.value = 0
  releaseButtons(dut)
  await ClockCycles(dut.clk, 10, False)
  dut.rst_n.value = 1
  assert internalDigits(dut) == hex(1)

#############################################################################
#### Tests begin here #######################################################

@cocotb.test()
async def test_dice_activehighbuttons(dut):
  dut._log.info("Testing active high buttons")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 1 # Configure buttons as active high, outputs as active low
  await reset(dut)
  digitsShown_task = cocotb.start_soon(checkDigitsShown(dut))
  segmentsShown_task = cocotb.start_soon(checkSegmentOutputs(dut))
  dut._log.info("Running test")
  await testAllButtons(dut)
  dut._log.info("End test")

@cocotb.test()
async def test_dice_activelowbuttons(dut):
  dut._log.info("Testing active low buttons")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 0 # Configure buttons as active low, outputs as active low
  activeLevel=0
  commonLevel=0
  await reset(dut)
  digitsShown_task = cocotb.start_soon(checkDigitsShown(dut))
  segmentsShown_task = cocotb.start_soon(checkSegmentOutputs(dut))
  dut._log.info("Running test")
  await testAllButtons(dut)
  dut._log.info("End test")

@cocotb.test()
async def test_dice_activehighsegments(dut):
  dut._log.info("Testing active high segment outputs")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 2+1 # Configure buttons as active high, segment outputs as active high
  await reset(dut)
  digitsShown_task = cocotb.start_soon(checkDigitsShown(dut))
  segmentsShown_task = cocotb.start_soon(checkSegmentOutputs(dut))
  dut._log.info("Running test")
  await testAllButtons(dut)
  dut._log.info("End test")
  
@cocotb.test()
async def test_dice_activehighcommons(dut):
  dut._log.info("Testing active high common outputs")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 4+1 # Configure buttons as active high, common outputs as active high
  await reset(dut)
  digitsShown_task = cocotb.start_soon(checkDigitsShown(dut))
  segmentsShown_task = cocotb.start_soon(checkSegmentOutputs(dut))
  dut._log.info("Running test")
  await testAllButtons(dut)
  dut._log.info("End test")

@cocotb.test()
async def test_dice_activehighboth(dut):
  dut._log.info("Testing active high common and segment outputs")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 4+2+1 # Configure buttons as active high, common and segment outputs as active high
  await reset(dut)
  digitsShown_task = cocotb.start_soon(checkDigitsShown(dut))
  segmentsShown_task = cocotb.start_soon(checkSegmentOutputs(dut))
  dut._log.info("Running test")
  await testAllButtons(dut)
  dut._log.info("End test")

@cocotb.test()
async def test_dice_timeout(dut):
  dut._log.info("Testing timeout after button release")
  dut._log.info("Setting up test")
  clock = Clock(dut.clk, 30, units="us") # Approximation of 32768 Hz
  cocotb.start_soon(clock.start())
  dut.cfg.value = 4+2+1 # Configure buttons as active high, common and segment outputs as active high
  await reset(dut)
  dut._log.info("Running test")
  dut._log.info("Pressing button")
  dut.btn100.value = 1
  await Timer(1, units='sec')
  assert noDigitsShown(dut);
  dut._log.info("Releasing button")
  dut.btn100.value = 0
  for i in range(0,4):
    await Timer(1, units='sec')
    # Digits should be shown now
    if noDigitsShown(dut):  # if no digit is shown, maybe this a blanked digit10. Wait for the other digit
      await Edge(dut.clk);
      await Timer(1, units='us');
      assert not noDigitsShown(dut);
  # Let the timeout expire
  await Timer(6,units='sec')
  assert noDigitsShown(dut);
  
  dut._log.info("End test")
