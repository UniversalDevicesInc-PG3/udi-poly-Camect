
from udi_interface import LOGGER
from node_funcs import get_valid_node_name
from nodes import BaseNode,DetectedObject
from const import DETECTED_OBJECT_MAP, OBJECT_ALIASES, normalize_object_name

class Camera(BaseNode):
    def __init__(self, controller, host, address, cam):
        self.ready = False
        self.controller = controller
        self.host = host
        self.cam = cam
        self.detected_obj_by_type = {}
        cam_name = cam['name'] if cam is not None else address
        super(Camera, self).__init__(controller.poly, address, address, get_valid_node_name(cam_name))
        self.lpfx = '%s:%s' % (self.address,self.name)
        controller.poly.subscribe(controller.poly.START, self.start, address)

    def activate(self):
        """Initialize a rehydrated camera when START has already fired."""
        if not self.ready:
            self.start()

    def start(self):
        if self.ready:
            return
        LOGGER.debug(f'{self.lpfx} Starting...')
        if self.cam is not None:
            self.update_status(self.cam)
        self.set_driver('ALARM',0)
        for cat in DETECTED_OBJECT_MAP:
            address = f'{self.address}_{cat}'[:14]
            dobj = DetectedObject(self.controller, self, address, cat)
            if self.controller.poly.getNode(address):
                dobj.activate()
            else:
                self.controller.add_node(address, dobj)
            for otype in DETECTED_OBJECT_MAP[cat]:
                self.detected_obj_by_type[otype] = dobj
        for alias, canonical in OBJECT_ALIASES.items():
            if canonical in self.detected_obj_by_type:
                self.detected_obj_by_type[alias] = self.detected_obj_by_type[canonical]
        LOGGER.debug(f'{self.lpfx} Done...')
        self.ready = True

    def query(self,command=None):
        if self.cam is None:
            LOGGER.error(f"{self.lpfx}: Camera no longer exists on Camect hub")
            self.reportDrivers()
            return
        self.update_status(self.host.list_camera(self.cam['id']),report=False)
        self.reportDrivers()

    def update_status(self,cam,report=True):
        if cam is None:
            self.controller.error("Camera info not defined, was it deleted from Camect?  Please report this to the developer")
            self.set_driver('ST', 0, report=report)
            return
        self.cam = cam
        self.set_driver('ST',0   if cam['disabled']           else 1, report=report)
        self.set_driver('MODE',0 if cam['is_alert_disabled']  else 1, report=report)
        self.set_driver('GPV', 1 if cam['is_streaming']       else 0, report=report)
        self.set_driver('ALARM', 0)

    def callback(self,event):
        LOGGER.debug(f"{self.lpfx} type={event['type']}")
        if event['type'] == 'alert':
            if 'detected_obj' in event:
                self.detected_obj(event['detected_obj'])
            else:
                self.controller.error(f"Unknown alert, no detected_obj in {event}")
        elif event['type'] == 'alert_disabled':
            self.set_driver('MODE',0)
        elif event['type'] == 'alert_enabled':
            self.set_driver('MODE',1)
        elif event['type'] == 'camera_offline':
            self.set_driver('ST',0)
        elif event['type'] == 'camera_online':
            self.set_driver('ST',1)
        else:
            msg = f"Unknown event type {event['type']} in {event}"
            self.controller.error(msg)
            
    def detected_obj(self,object_list):
        LOGGER.debug(f"{self.lpfx} {object_list}")
        for obj in object_list:
            obj = normalize_object_name(obj)
            if obj in self.detected_obj_by_type:
                LOGGER.debug(f"{self.lpfx} {obj}")
                self.set_driver('ALARM',1)
                self.detected_obj_by_type[obj].turn_on(obj)
            else:
                self.error(f"Unsupported detected object '{obj}'")

    def error(self,text):
        self.controller.error(f"{self.cam['name']}: {text}")

    def cmd_alert_on(self, command):
        LOGGER.info("")
        if self.cam is None:
            return
        self.host.enable_alert(self.cam['id'])
        self.set_driver('MODE', 1)

    def cmd_alert_off(self, command):
        LOGGER.info("")
        if self.cam is None:
            return
        self.host.disable_alert(self.cam['id'])
        self.set_driver('MODE', 0)

    def cmd_enable_on(self, command):
        pass

    def cmd_enable_off(self, command):
        pass

    hint = [1,2,3,4]
    drivers = [
        {'driver': 'ST',    'value': 0, 'uom': 2,  'name': 'Enabled'},
        {'driver': 'ALARM', 'value': 0, 'uom': 2,  'name': 'Detected'},
        {'driver': 'MODE',  'value': 0, 'uom': 2,  'name': 'Alerting'},
        {'driver': 'GPV',   'value': 0, 'uom': 2,  'name': 'Streaming'},
        ]
    id = 'camera'
    commands = {
                    'DON': cmd_alert_on,
                    'DOF': cmd_alert_off,
                    'SET_DISABLE_ON': cmd_enable_on,
                    'SET_DISABLE_OFF': cmd_enable_off,
                }
