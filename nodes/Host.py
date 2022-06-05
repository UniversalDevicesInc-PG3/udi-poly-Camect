

import time
from udi_interface import LOGGER
from nodes import BaseNode

# My Nodes
from nodes import Camera
from const import HOST_MODE_MAP
# My functions
from node_funcs import id_to_address,get_valid_node_name

class Host(BaseNode):
    id = 'host'
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2}, 
        {'driver': 'MODE', 'value': 1, 'uom': 25}, 
    ]

    def __init__(self, controller, address, host, camect_obj, new=True):
        self.ready      = False
        self.controller = controller
        self.host       = host
        self.camect     = camect_obj # The camect api handle
        self.new        = new
        self.cams_by_id = {} # The hash of camera nodes by id
        name = get_valid_node_name('Camect '+self.camect.get_name())
        LOGGER.info(f'address={address} name={name} ')
        super(Host, self).__init__(controller.poly, address, address, name)

        controller.poly.subscribe(controller.poly.START, self.start, address)

    def start(self):
        LOGGER.info(f'Started Camect Host {self.address}:{self.name}')
        self.set_driver('ST',1)
        self.set_mode_by_name(self.camect.get_mode())
        # We only rediscover a newly added device
        if self.new:
            self.discover()
        else:
            self.add_saved()
        self.camect.add_event_listener(self.callback)
        self.ready = True

    def list_cameras(self):
        try:
            return self.camect.list_cameras()
        except Exception as err:
            LOGGER.error(f'list_cameras: {err}')
        self.camect = False
        return []

    def list_camera(self,camid):
        for cam in self.list_cameras():
            if cam['id'] == camid:
                return cam
        return None

    def update_status(self,cams=False,report=True):
        LOGGER.debug(f'{self.lpfx} cams={cams} report={report}')
        # Reconnect?
        if self.camect is False:
            LOGGER.warning(f'{self.lpfx}: reconnecting since camect={self.camect}')
            self.camect = self.controller.reconnect_host(self.host)        
        if self.camect is False:
            self.set_driver('ST',0,report=report)
            return False
        self.set_driver('ST',1,report=report)
        if cams:
            LOGGER.debug(f'{self.lpfx} Updating cams... {cams}')
            for cam in self.list_cameras():
                if cam['id'] in self.cams_by_id:
                    #LOGGER.debug(f"{self.lpfx}: Check camera: {cam}")
                    self.cams_by_id[cam['id']].update_status(cam)
        return True

    def shortPoll(self):
        # We have to update camera status on because there are no callbacks
        # for streaming, but disabled for now to reduce traffic.
        self.update_status(cams=False)

    def query(self,command=None):
        self.update_status(report=False)
        self.reportDrivers()

    def set_mode_by_name(self,mname):
        LOGGER.debug(f'{self.lpfx}: mode={mname}')
        if mname in HOST_MODE_MAP:
            self.set_mode(HOST_MODE_MAP[mname])
            return
        LOGGER.error(f'{self.lpfx}: Unknown Host Mode Name "{mname}"')

    def set_mode(self,val=None):
        LOGGER.debug(f'{self.lpfx}: val={val}')
        if val is None:
            val = self.get_driver('MODE')
        self.set_driver('MODE',val)

    def callback(self,event):
        # {'type': 'alert', 'desc': 'Out Front Door just saw a person.', 'url': 'https://home.camect.com/home/...', 
        # 'cam_id': '96f69defdef1d0b6602a', 'cam_name': 'Out Front Door', 'detected_obj': ['person']}
        LOGGER.debug(f'{event}')
        try:
            if event['type'] == 'mode':
                # Can't really use this: {'type': 'mode', 'desc': 'HOME'}
                self.set_mode_by_name(event['desc'])
                self.controller.set_mode_all()
            elif 'cam_id' in event:
                # Anything with cam get's passed to the camera
                if event['cam_id'] in self.cams_by_id:
                    self.cams_by_id[event['cam_id']].callback(event)
                else:
                    LOGGER.warning(f"{self.lpfx}: Event for unknown cam_id={event['cam_id']} will add it now: {event}")
                    # Must add the new camera to this host
                    self.get_and_add_camera(event['cam_id'])

            else:
                LOGGER.error(f'{self.lpfx}: Unknwon event, not type=mode or cam_id: {event}')
        except:
            LOGGER.error(f'{self.lpfx}: in callback: ',exc_info=True)

    def add_saved(self):
        LOGGER.info('{self.lpfx}: Adding saved cameras...')
        for cam in self.controller.get_saved_cameras(self):
            LOGGER.debug(f"{self.lpfx}: Adding cam {cam['node_address']} {cam['name']}")
            self.cams_by_id[cam['id']] = self.controller.poly.addNode(Camera(self.controller, self, cam['node_address'], cam))

    def discover(self):
        # TODO: Keep cams_by_id in DB to remember across restarts and discovers...
        LOGGER.info('started')
        for cam in self.list_cameras():
            LOGGER.debug(f"{self.lpfx}: Check camera: {cam}")
            # Only add enabled cameras?
            if not cam['disabled']:
                self.add_camera(cam)
        LOGGER.info('completed')

    def get_and_add_camera(self,camid):
        self.add_camera(self.list_camera(camid))

    def add_camera(self,cam):
        cam_address = self.controller.get_cam_address(cam,self)
        LOGGER.debug(f"Adding cam {cam_address} {cam['name']}")
        self.cams_by_id[cam['id']] = self.controller.poly.addNode(Camera(self.controller, self, cam_address, cam))

    def enable_alert(self, cam_id):
        LOGGER.info(f"{self.lpfx}: {cam_id}")
        return self.camect.enable_alert([cam_id],"nodeserver")

    def disable_alert(self, cam_id):
        LOGGER.info(f"{self.lpfx}: {cam_id}")
        return self.camect.disable_alert([cam_id],"nodeserver")

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def cmd_set_mode(self,command):
        LOGGER.debug(f'{self.lpfx}: {command}')
        #self.set_mode(int(command.get('value'))) # Don't set it, let the callback handle it.
        val = int(command.get('value'))
        for mname in HOST_MODE_MAP:
            if HOST_MODE_MAP[mname] == val:
                LOGGER.info(f"{self.lpfx}: Setting Camect Mode={mname}")
                self.camect.set_mode(mname)
                return
        LOGGER.error(f'{self.lpfx}: Unknown Mode Value {val}')

    def cmd_discover(self,command):
        LOGGER.debug(f'{self.lpfx}')
        self.discover()

    commands = {
        'QUERY': query,
        'DISCOVER': cmd_discover,
        'SET_MODE': cmd_set_mode
    }
