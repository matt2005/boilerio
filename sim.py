#!/usr/bin/env python

""" A very basic simple room simulation.

Intended to guide setting of constants for PID controller.  Constants
came from (unscientific) meausrement of a real room and then curve-
fitting.
"""

import argparse
import datetime
import random
import maintaintemp

RAD_RAMPUP_TIME = 6
RAD_RAMPDOWN_TIME = 25
RAD_MAX_TEMP = 60

class FakeBoiler(object):
    def __init__(self, house):
        self.house = house

    def command(self, cmd):
        if cmd == 'O':
            self.on()
        elif cmd == 'X':
            self.off()

    def on(self):
        self.house.heating(True)

    def off(self):
        self.house.heating(False)

class House(object):
    def __init__(self, start_temp):
        self.outside_temp = 5
        self.room_temp = start_temp
        self.heating_on = False
        self.rad_temp_delta = 0

        # Constants of heat gain/loss
        self.d_house = 0.000270974484739
        self.d_rad = 0.000455917702374

    # Dumb linear ramp-up/down for radiator heat:
    def update_rad(self):
        if self.heating_on:
            step = (RAD_MAX_TEMP - self.room_temp) / RAD_RAMPUP_TIME
            self.rad_temp_delta = min(RAD_MAX_TEMP - self.room_temp,
                                      self.rad_temp_delta + step)
        else:
            step = (RAD_MAX_TEMP - self.room_temp) / RAD_RAMPDOWN_TIME
            self.rad_temp_delta = max(0, self.rad_temp_delta - step)

    def update_room(self):
        rad_output = self.d_rad * self.rad_temp_delta
        delta_t = self.room_temp - self.outside_temp
        room_loss = -1 * self.d_house * delta_t

        self.room_temp += room_loss + rad_output

    # One minute passes in the simulation
    def tick(self):
        self.update_rad()
        self.update_room()

    def heating(self, heating):
        self.heating_on = heating

def run_simulation(start_temp, target_temp, sim_duration_mins,
                   randomness):
    state = maintaintemp.State()
    house = House(start_temp)
    boiler = FakeBoiler(house)
    state.boilerControl = boiler
    state.updateTargetTemperature(target_temp)

    # Start time doesn't really matter:
    now = start = datetime.datetime(2000, 1, 1, 0, 0)
    for _ in range(sim_duration_mins):
        boiler_on = 0
        for _ in range(60):
            now = now + datetime.timedelta(0, 1)
            state.now = now
            maintaintemp.period(state)
            boiler_on += 1 if house.heating_on else 0
        house.tick()
        if randomness:
            room_temp_with_error = house.room_temp - 0.05 + 0.1 * random.random()
        else:
            room_temp_with_error = house.room_temp
        state.updateTemperature(room_temp_with_error)
        dutyCycle = state.pwmDutyCycle.total_seconds() \
                    if state.pwmDutyCycle else 0
        dutyCycle = float(dutyCycle) / maintaintemp.PWM_PERIOD.total_seconds()
        print (now - start).total_seconds() / 60, boiler_on, \
              dutyCycle, house.room_temp, room_temp_with_error, \
              state.pid.last_prop, state.pid.error_integral, \
              state.pid.last_diff

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", dest="random", action="store_true",
                        help="Incorporate randomness into fake readings")
    parser.add_argument("start_temp", type=float)
    parser.add_argument("target_temp", type=float)
    parser.add_argument("runtime", type=int)
    args = parser.parse_args()
    run_simulation(args.start_temp, args.target_temp, args.runtime,
                   args.random)
