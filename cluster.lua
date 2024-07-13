
local M = {}

local hasShiftLights = false
local function init()
  local shiftLightControllers = controller.getControllersByType("shiftLights")
  hasShiftLights = shiftLightControllers and #shiftLightControllers > 0
end

local function reset() end
local function getAddress()        return "127.0.0.1" end         -- return settings.getValue("protocols_cluster_address") end   
local function getPort()           return 4567 end            -- return settings.getValue("protocols_cluster_port") end      
local function getMaxUpdateRate()   return 60 end            -- return settings.getValue("protocols_cluster_maxUpdateRate") end  

local function isPhysicsStepUsed()
  return false -- use graphics step. performance cost is ok. the update rate could reach UP TO min(getMaxUpdateRate(), graphicsFramerate)
  --return true-- use physics step. performance cost is big. the update rate could reach UP TO min(getMaxUpdateRate(), 2000 Hz)
end

local function getStructDefinition()
  return [[
      char           gear;            // [0]  Gear selector position, P/R/N/D/S/M/L
      char           gearIndex;       // [1]  Gear 1/2/3/4/5/6/7, null if not a manual car, or in sport/manual mode
      float          speed;           // [2]  M/S
      float          rpm;             // [3]  RPM
      float          turbo;           // [4]  BAR
      float          engTemp;         // [5]  C
      float          fuel;            // [6]  0 to 1
      float          oilPressure;     // [7]  BAR // N/A, hardcoded to 0
      float          oilTemp;         // [8]  C
      unsigned       dashLights;      // [9]  Dash lights available (see DL_x below)
      unsigned       showLights;      // [10]  Dash lights currently switched on
      float          throttle;        // [11]  0 to 1
      float          brake;           // [12]  0 to 1
      float          clutch;          // [13]  0 to 1
  ]]
end



--[[

// bit 0    - shift light
// bit 1    - full beam
// bit 2    - handbrake
// bit 3    - pit speed limiter // N/A
// bit 4    - TC active or switched off
// bit 5    - left turn signal
// bit 6    - right turn signal
// bit 7    - shared turn signal // N/A
// bit 8    - oil pressure warning
// bit 9    - battery warning
// bit 10   - ABS active or switched off
// bit 11   - ignition switch state
// bit 12   - tpms light
// bit 13   - cel
// bit 14   - fog lights
// bit 15   - lowbeam/parking lights

]]


-- DL_x - bits for lights
local DL_SHIFT = 2 ^ 0
local DL_FULLBEAM = 2 ^ 1
local DL_HANDBRAKE = 2 ^ 2
local DL_TC = 2 ^ 4
local DL_SIGNAL_L = 2 ^ 5
local DL_SIGNAL_R = 2 ^ 6
local DL_OILWARN = 2 ^ 8
local DL_BATTERY = 2 ^ 9
local DL_ABS = 2 ^ 10
local DL_IGNITION = 2 ^ 11
local DL_LOWPRESSURE = 2 ^ 12
local DL_CHECKENGINE = 2 ^ 13
local DL_FOG = 2 ^ 14
local DL_LOWBEAM = 2 ^ 15

local function fillStruct(o, dtSim)
  if not electrics.values.watertemp then
    -- vehicle not completly initialized, skip sending package
    return
  end
  o.gear = string.byte(electrics.values.gear)
  o.gearIndex = electrics.values.gearIndex
  o.speed = electrics.values.wheelspeed or electrics.values.airspeed
  o.rpm = electrics.values.rpm or 0
  o.turbo = (electrics.values.turboBoost or 0) / 14.504
  o.engTemp = electrics.values.watertemp or 0
  o.fuel = electrics.values.fuel or 0
  o.oilPressure = 0 -- TODO
  o.oilTemp = electrics.values.oiltemp or 0

  -- the lights

  if hasShiftLights then
    o.dashLights = bit.bor(o.dashLights, DL_SHIFT)
    if electrics.values.shouldShift then
      o.showLights = bit.bor(o.showLights, DL_SHIFT)
    end
  end

  o.dashLights = bit.bor(o.dashLights, DL_FULLBEAM)
  if electrics.values.highbeam ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_FULLBEAM)
  end

  o.dashLights = bit.bor(o.dashLights, DL_HANDBRAKE)
  if electrics.values.parkingbrake ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_HANDBRAKE)
  end

  hasESC = electrics.values.hasESC
  if hasESC then
    o.dashLights = bit.bor(o.dashLights, DL_TC)
    if electrics.values.esc ~= 0 or electrics.values.tcs ~= 0 then
      o.showLights = bit.bor(o.showLights, DL_TC)
    end
  end

  o.dashLights = bit.bor(o.dashLights, DL_SIGNAL_L)
  if electrics.values.signal_L ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_SIGNAL_L)
  end

  o.dashLights = bit.bor(o.dashLights, DL_SIGNAL_R)
  if electrics.values.signal_R ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_SIGNAL_R)
  end

  o.dashLights = bit.bor(o.dashLights, DL_OILWARN)
  if electrics.values.oil ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_OILWARN)
  end
  
  o.dashLights = bit.bor(o.dashLights, DL_BATTERY)
  if electrics.values.engineRunning == 0 then
    o.showLights = bit.bor(o.showLights, DL_BATTERY)
  end

  local hasABS = electrics.values.hasABS or false
  if hasABS then
    o.dashLights = bit.bor(o.dashLights, DL_ABS)
    if electrics.values.abs ~= 0 then
      o.showLights = bit.bor(o.showLights, DL_ABS)
    end
  end
  
  o.dashLights = bit.bor(o.dashLights, DL_IGNITION)
  if electrics.values.ignition ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_IGNITION)
  end

  o.dashLights = bit.bor(o.dashLights, DL_LOWPRESSURE)
  if electrics.values.lowpressure ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_LOWPRESSURE)
  end

  o.dashLights = bit.bor(o.dashLights, DL_CHECKENGINE)
  if electrics.values.checkengine ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_CHECKENGINE)
  end

  o.dashLights = bit.bor(o.dashLights, DL_FOG)
  if electrics.values.fog ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_FOG)
  end

  o.dashLights = bit.bor(o.dashLights, DL_LOWBEAM)
  if electrics.values.lowbeam ~= 0 then
    o.showLights = bit.bor(o.showLights, DL_LOWBEAM)
  end
  
  o.throttle = electrics.values.throttle
  o.brake = electrics.values.brake
  o.clutch = electrics.values.clutch

end

M.init = init
M.reset = reset
M.getAddress = getAddress
M.getPort = getPort
M.getMaxUpdateRate = getMaxUpdateRate
M.getStructDefinition = getStructDefinition
M.fillStruct = fillStruct
M.isPhysicsStepUsed = isPhysicsStepUsed

return M
