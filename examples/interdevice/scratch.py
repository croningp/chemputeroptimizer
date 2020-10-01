print("hi")

from logging import DEBUG, basicConfig
from sys import base_exec_prefix
from chempiler import Chempiler


from os import path

import ChemputerAPI
import SerialLabware

root = path.abspath(path.curdir)
output_dir = path.join(path.curdir, 'logs')
graphml_file = "C:\\Users\\group\\Code\\chemputeroptimizer\\examples\\interdevice\\mini_36.json"

chempiler = Chempiler("test_miniputer", graphml_file, output_dir,
                      simulation=False, device_modules=[ChemputerAPI, SerialLabware])


valves = ["valve_1", "valve_1", "valve_1"]

import random
import logging

logger = logging.getLogger()

logging.basicConfig(level=DEBUG)

chempiler.move("water", "waste_3", 50, speed=50)

for valve in valves:
    for _ in range(10):
        chempiler[valve].move_to_position(random.randint(0, 5))
        chempiler[valve].wait_until_ready()


