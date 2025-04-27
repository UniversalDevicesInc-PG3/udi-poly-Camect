
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

    def __init__(self, controller, primary, address, otype):
        self.id = otype
        self.controller = controller
        self.map = DETECTED_OBJECT_MAP[otype]
        LOGGER.debug(f"Adding DetectedObject {otype} for {primary.address}:{primary.name} address={address}")
        name    = f'{primary.name} {otype}'
        super(DetectedObject, self).__init__(controller.poly, primary.address, address, name)
        self.dname_to_driver = {}
        self.lpfx = '%s:%s' % (self.address,self.name)
        pdrv = dict()
        if self.controller.has_st_bug:
            odrivers = controller.poly.db_getNodeDrivers(address)
            LOGGER.debug(f"{self.lpfx} odrivers={odrivers}")
            if odrivers is not None:
                for odrv in odrivers:
                    pdrv[odrv['driver']] = odrv['value']
        for obj_name in self.map:
            dv = 'GV' + str(self.map[obj_name]['num'])
            val = pdrv[dv] if dv in pdrv else 0
            self.drivers.append({'driver':  dv, 'value': val, 'uom': 2})
            # Hash of my detected objects to the driver
            self.dname_to_driver[obj_name] = dv
        controller.poly.subscribe(controller.poly.START, self.start, address)

    def start(self):
        LOGGER.debug(f'{self.lpfx}')
        if not self.controller.has_st_bug:
            self.clear(report=False)
            self.reportDrivers()

    def clear(self,report=True,force=False):
        LOGGER.debug(f"{self.lpfx} report={report} force={force} ST={self.get_driver('ST')}")
        if force or self.get_driver('ST') is None or int(self.get_driver('ST')) == 1:
            LOGGER.debug(f'{self.lpfx}')
            self.set_driver('ST', 0, report=report)
            #self.reportCmd("DOF",2)
            for obj in self.dname_to_driver:
                self.set_driver(self.dname_to_driver[obj], 0, report=report)

    # Used by turn_on and all cmd_on methods
    def turn_on_d(self,driver):
        LOGGER.debug(f"{self.lpfx} driver={driver}")
        if driver == 'DON':
            # Due to a bug in current version of ISY 5.4.4 when
            # we send Status, it triggers a Control program so
            # if status is already on, just send a control.
            if (int(self.get_driver('ST')) == 0):
                self.set_driver('ST',1)
            else:
                # Already on, send a Control
                LOGGER.debug(f"{self.lpfx} reportCmd({driver})")
                self.reportCmd(driver)
        else:
            # Clear all drivers if they are on
            if int(self.get_driver('ST')) == 1:
                self.clear()
            # ST means something detected
            self.set_driver('ST',1)
            self.set_driver(driver,1)
            # Send a Control
            LOGGER.debug(f"{self.lpfx} reportCmd(ST,1.2)")
            self.reportCmd('ST',1,2)
            LOGGER.debug(f"{self.lpfx} reportCmd({driver},1.2)")
            self.reportCmd(driver,1,2)

    # This is called by parent when object is detected
    def turn_on(self,obj):
        LOGGER.debug(f"{self.lpfx}")
        self.turn_on_d(self.dname_to_driver[obj])

    # This is called by parent when object is no longer detected
    def turn_off(self,obj):
        LOGGER.debug(f"{self.lpfx}")
        self.set_driver(self.dname_to_driver[obj],0)
        #self.reportCmd("DOF",2)

    def cmd_on(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('DON')

    def cmd_on_0(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV0')

    def cmd_on_1(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV1')

    def cmd_on_2(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV2')

    def cmd_on_3(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV3')

    def cmd_on_4(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV4')

    def cmd_on_5(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV5')

    def cmd_on_6(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV6')

    def cmd_on_7(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV7')

    def cmd_on_8(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV8')

    def cmd_on_9(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV9')

    def cmd_on_10(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV10')

    def cmd_on_11(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV11')

    def cmd_on_12(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV12')

    def cmd_on_13(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV13')

    def cmd_on_14(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV14')

    def cmd_on_15(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command}")
        self.turn_on_d('GV15')

    def cmd_off(self, command=None):
        LOGGER.debug(f"{self.lpfx} command={command} ST={self.get_driver('ST')}")
        self.set_driver('ST', 0)
        for key in self.dname_to_driver:
            self.set_driver(self.dname_to_driver[key],0)

    def query(self,command=None):
        LOGGER.debug(f'{self.lpfx}')
        self.reportDrivers()

    commands = {
        'DON': cmd_on,
        'DOF': cmd_off,
        'GV0': cmd_on_0,
        'GV1': cmd_on_1,
        'GV2': cmd_on_2,
        'GV3': cmd_on_3,
        'GV4': cmd_on_4,
        'GV5': cmd_on_5,
        'GV6': cmd_on_6,
        'GV7': cmd_on_7,
        'GV8': cmd_on_8,
        'GV9': cmd_on_9,
        'GV10': cmd_on_10,
        'GV11': cmd_on_11,
        'GV12': cmd_on_12,
        'GV13': cmd_on_13,
        'GV14': cmd_on_14,
        'GV15': cmd_on_15,
    }
    hint = [1,2,3,4]
