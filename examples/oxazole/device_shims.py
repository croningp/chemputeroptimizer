from ChemputerAPI import ChemputerDevice
from AnalyticalLabware import IDEXMXIIValve, SpinsolveNMR, HPLCController

class ChemputerIDEX(IDEXMXIIValve, ChemputerDevice):
    def __init__(self, name, address, port=5000):
        ChemputerDevice.__init__(self, name)
        IDEXMXIIValve.__init__(
            self,
            mode="ethernet",
            address=address,
            connect_on_instantiation=False,
        )

    @property
    def capabilities(self):
        return [("sink", 0)]
    
    def wait_until_ready(self):
        pass

class ChemputerNMR(SpinsolveNMR, ChemputerDevice):
    def __init__(self, name):
        ChemputerDevice.__init__(self, name)
        SpinsolveNMR.__init__(self)

    @property
    def capabilities(self):
        return [("sink", 0)]



class FinderIDEX(IDEXMXIIValve, ChemputerDevice):
    def __init__(self, name, address, port=5000):
        ChemputerDevice.__init__(self, name)
        IDEXMXIIValve.__init__(
            self,
            #name,
            mode="ethernet",
            address="192.168.1.99",
            connect_on_instantiation=False,
            #connection_mode="tcpip",
            #connection_parameters={"address": address, "port": port},
        )

    @property
    def capabilities(self):
        return [("sink", 0)]

    def wait_until_ready(self):
        pass


class SimFinderIDEX(IDEXMXIIValve, ChemputerDevice):
    def __init__(self, name, address, port=5000):
        ChemputerDevice.__init__(self, name)

    @property
    def capabilities(self):
        return [("sink", 0)]

    def wait_until_ready(self):
        pass

    def sample(self):
        self.logger.info("Valving sampling!")


class FinderNMR(SpinsolveNMR, ChemputerDevice):
    def __init__(self, name):
        ChemputerDevice.__init__(self, name)
        SpinsolveNMR.__init__(self)

    @property
    def capabilities(self):
        return [("sink", 0)]
