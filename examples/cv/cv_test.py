#from chemputeroptimizer import OptimizerPlatform
from xdl import XDL
from chempiler import Chempiler
import ChemputerAPI

from AnalyticalLabware.devices import chemputer_devices

GRAPH = 'examples/cv/new_graph.json'
cv_template_folder = 'examples/cv/templates/'
c = Chempiler(
    experiment_code='ABC',
    graph_file=GRAPH,
    output_dir='output_dir',
    simulation=False,
    device_modules=[ChemputerAPI, chemputer_devices],
    cv_template_folder=cv_template_folder
)

# for usb camera, uncomment and use below command
#c.start_recording()
# start recording using Camera 1
c.start_recording("rtsp://ubnt:ubnt@192.168.1.23:554/s0")

#start anomaly detection system and recording using Camera 2
c.start_recording("rtsp://ubnt:ubnt@192.168.1.30:554/s0")

c.wait(50)
#C:/Users/group/Miniconda3/Scripts/activate
# conda activate cv
# python examples/cv/cv_test.py