
from nodes.BaseNode import BaseNode
from udi_interface import LOGGER
from nodes import BaseNode
from node_funcs import id_to_address,get_valid_node_name
from const import DETECTED_OBJECT_MAP

class DetectedObject(BaseNode):
    id = 'objdet' # Placeholder, gets overwritten in __init__
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2}, # Enabled
    ]

    def __init__(self, controller, primary, otype):
        self.id = otype
        self.map = DETECTED_OBJECT_MAP[otype]
        LOGGER.debug(f"Adding DetectedObject {otype} for {primary.address}:{primary.name}")
        address = f'{primary.address}_{otype}'[:14]
        name    = f'{primary.name} {otype}'
        super(DetectedObject, self).__init__(controller.poly, primary.address, address, name)
        self.dname_to_driver = {}
        self.lpfx = '%s:%s' % (self.address,self.name)
        for obj_name in self.map:
            dv = 'GV' + str(self.map[obj_name]['num'])
            self.drivers.append({'driver':  dv, 'value': 0, 'uom': 2})
            # Hash of my detected objects to the driver
            self.dname_to_driver[obj_name] = dv

        controller.poly.subscribe(controller.poly.START, self.start, address)

    def start(self):
        LOGGER.debug(f'{self.lpfx}')
        self.set_driver('ST',0)
        for dn in self.dname_to_driver:
            self.set_driver(self.dname_to_driver[dn], 0)

    def clear(self):
        if int(self.get_driver('ST')) == 1:
            LOGGER.debug(f'{self.lpfx}')
            self.reportCmd("DOF",2)
            for obj in self.dname_to_driver:
                self.set_driver(self.dname_to_driver[obj], 0)

    # This is called by parent when object is detected
    def turn_on(self,obj):
        LOGGER.debug(f"{self.lpfx}")
        self.reportCmd("DON",2)
        self.set_driver(self.dname_to_driver[obj],1)

    # This is called by parent when object is no longer detected
    def turn_off(self,obj):
        LOGGER.debug(f"{self.lpfx}")
        self.reportCmd("DOF",2)
        self.set_driver(self.dname_to_driver[obj],0)

    def cmd_on(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command} ST={self.get_driver('ST')}")
        self.set_driver('ST', 1)

    def cmd_off(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command} ST={self.get_driver('ST')}")
        self.set_driver('ST', 1)

    def query(self,command=None):
        LOGGER.debug(f'{self.lpfx}')
        self.reportDrivers()

    hint = [1,2,3,4]
    commands = {
                    'DON': cmd_on,
                    'DOF': cmd_off,
                }
