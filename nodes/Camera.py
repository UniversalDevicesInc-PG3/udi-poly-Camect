
from udi_interface import LOGGER
from node_funcs import id_to_address,get_valid_node_name
from nodes import BaseNode,DetectedObject
from const import DETECTED_OBJECT_MAP

class Camera(BaseNode):
    def __init__(self, controller, host, address, cam):
        self.ready = False
        #print("%s(%s) @%s(%s)" % (cam["name"], cam["make"], cam["ip_addr"], cam["mac_addr"]))
        self.controller = controller
        self.host = host
        self.cam = cam
        self.detected_obj_by_type = {}
        super(Camera, self).__init__(controller.poly, address, address, get_valid_node_name(cam['name']))
        self.lpfx = '%s:%s' % (self.address,self.name)

        controller.poly.subscribe(controller.poly.START, self.start, address)

    def start(self):
        LOGGER.debug(f'{self.lpfx} Starting...')
        self.update_status(self.cam)
        self.set_driver('ALARM',0)
        for cat in DETECTED_OBJECT_MAP:
            node = self.controller.poly.addNode(DetectedObject(self.controller, self, cat))
            # Keep track of which node handles which detected object type.
            for otype in DETECTED_OBJECT_MAP[cat]:
                self.detected_obj_by_type[otype] = node
        LOGGER.debug(f'{self.lpfx} Done...')
        self.ready = True

    def query(self,command=None):
        self.update_status(self.host.list_camera(self.cam['id']),report=False)
        self.reportDrivers()

    def update_status(self,cam,report=True):
        if cam is None:
            LOGGER.error("Camera info not defined, was it deleted from Camect?  Please report this to the developer")
            return
        LOGGER.debug(f'{self.lpfx}: cam={cam}')
        LOGGER.debug(f"{self.lpfx}: disabled={cam['disabled']} is_alert_disabled={cam['is_alert_disabled']} is_streaming={cam['is_streaming']}")
        self.set_driver('ST',0   if cam['disabled']           else 1, report=report)
        self.set_driver('MODE',0 if cam['is_alert_disabled']  else 1, report=report)
        self.set_driver('GPV', 1 if cam['is_streaming']       else 0, report=report)

    def callback(self,event):
        # {'type': 'alert', 'desc': 'Out Front Door just saw a person.', 'url': 'https://home.camect.com/home/...', 
        # 'cam_id': '96f69defdef1d0b6602a', 'cam_name': 'Out Front Door', 'detected_obj': ['person']}
        # {'type': 'alert_disabled', 'cam_id': '96f69defdef1d0b6602a', 'cam_name': 'Out Front Door'}
        # {'type': 'alert_enabled', 'cam_id': '96f69defdef1d0b6602a', 'cam_name': 'Out Front Door'}
        LOGGER.debug(f"{self.lpfx} type={event['type']}")
        if event['type'] == 'alert':
            if 'detected_obj' in event:
                self.detected_obj(event['detected_obj'])
            else:
                LOGGER.error(f"Unknown alert, no detected_obj in {event}")
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
            LOGGER.error(msg)
            self.controller.poly.Notices['callback'] = msg
            
    def detected_obj(self,object_list):
        LOGGER.debug(f"{self.lpfx} {object_list}")
        # Clear last detected objects
        # TODO: Would be better to timout and clear these during a short poll, but allow for user specified timeout?
        for cat in DETECTED_OBJECT_MAP:
            for otype in DETECTED_OBJECT_MAP[cat]:
                if otype in self.detected_obj_by_type:
                    self.detected_obj_by_type[otype].clear()
                else:
                    LOGGER.error(f"Internal error, no {otype} in dectected_obj_by_type dict?")
        # And set the current ones
        for obj in object_list:
            if obj in self.detected_obj_by_type:
                LOGGER.debug(f"{self.lpfx} {obj}")
                self.set_driver('ALARM',1)
                #self.set_driver('ALARM',DETECTED_OBJECT_MAP['obj'])
                self.detected_obj_by_type[obj].turn_on(obj)
            else:
                LOGGER.error(f"Unsupported detected object '{obj}'")

    def cmd_alert_on(self, command):
        LOGGER.info("")
        st = self.host.enable_alert(self.cam['id'])
        self.set_driver('MODE', 1)

    def cmd_alert_off(self, command):
        LOGGER.info("")
        st = self.host.disable_alert(self.cam['id'])
        self.set_driver('MODE', 0)

    def cmd_enable_on(self, command):
        #self.controller.enable_alert(self.cam['id'])
        #self.set_driver('GV0', 1)
        pass

    def cmd_enable_off(self, command):
        #self.controller.disable_alert(self.cam['id'])
        #self.set_driver('GV0', 0)
        pass

    hint = [1,2,3,4]
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2}, # Enabled
        {'driver': 'ALARM', 'value': 0, 'uom': 2}, # Detected
        {'driver': 'MODE', 'value': 0, 'uom': 2}, # Alerting
        {'driver': 'GPV', 'value': 0, 'uom': 2}, # Streaming
        {'driver': 'GV0', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV1', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV2', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV3', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV4', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV5', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV6', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV7', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV8', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV9', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV10', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV11', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV12', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV13', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV14', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV15', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV16', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV17', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV18', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV19', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV20', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV21', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV22', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV23', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV24', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV25', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV26', 'value': 0, 'uom': 2}, # 
        {'driver': 'GV27', 'value': 0, 'uom': 2}, # 
        ]
    id = 'camera'
    commands = {
                    'DON': cmd_alert_on,
                    'DOF': cmd_alert_off,
                    'SET_DISABLE_ON': cmd_enable_on,
                    'SET_DISABLE_OFF': cmd_enable_off,
                }
