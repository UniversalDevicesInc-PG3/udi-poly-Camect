
import time
from udi_interface import LOGGER
from nodes import BaseNode

# My Nodes
from nodes import Camera
from const import HOST_MODE_MAP
# My functions
from node_funcs import get_valid_node_name

# Host ST (UOM 25) — Camect Connected
ST_DISCONNECTED = 0
ST_CONNECTED = 1
ST_SYNCED = 2


class Host(BaseNode):
    id = 'host'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},
        {'driver': 'MODE', 'value': 1, 'uom': 25},
    ]

    def __init__(self, controller, address, host, port, camect_obj, new=True):
        self.ready      = False
        self.controller = controller
        self.host       = host
        self.port       = port
        self.camect     = camect_obj # The camect api handle
        self.new        = new
        self.cams_by_id = {} # The hash of camera nodes by id
        name = get_valid_node_name('Camect '+self.camect.get_name())
        LOGGER.info(f'address={address} name={name} ')
        super(Host, self).__init__(controller.poly, address, address, name)
        controller.poly.subscribe(controller.poly.START, self.start, address)

    def activate(self):
        """Initialize a rehydrated host when START has already fired."""
        if not self.ready:
            self.start()

    def start(self):
        if self.ready:
            return
        LOGGER.info(f'Started Camect Host {self.address}:{self.name}')
        self.set_connection_status()
        if self.camect is not False:
            self.set_mode_by_name(self.camect.get_mode())
        # We only rediscover a newly added device
        if self.new:
            self.discover()
        else:
            self.add_saved()
        if self.camect is not False:
            self._register_hub_listeners()
            # WS may already be open before the listener was attached
            self.set_connection_status()
        self.ready = True

    def _register_hub_listeners(self):
        """Attach event/connection listeners (new Hub after reconnect)."""
        if self.camect is False:
            return
        self.camect.add_event_listener(self.callback)
        add_conn = getattr(self.camect, 'add_connection_listener', None)
        if callable(add_conn):
            add_conn(self._on_ws_connection)

    def _on_ws_connection(self, connected):
        """Update ST when the event websocket connects or drops."""
        LOGGER.debug(f'{self.lpfx}: event stream connected={connected}')
        self.set_connection_status()

    def set_connection_status(self, report=True):
        """Set Host ST from HTTP client + event websocket state."""
        if self.camect is False:
            return self.set_driver('ST', ST_DISCONNECTED, report=report, uom=25)
        try:
            if self.camect.is_event_stream_connected():
                val = ST_SYNCED
            else:
                val = ST_CONNECTED
        except AttributeError:
            val = ST_CONNECTED
        return self.set_driver('ST', val, report=report, uom=25)

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
        reconnected = False
        # Reconnect?
        if self.camect is False:
            LOGGER.warning(f'{self.lpfx}: reconnecting since camect={self.camect}')
            self.camect = self.controller.reconnect_host(self.host, self.port)
            reconnected = self.camect is not False
        if self.camect is False:
            self.set_connection_status(report=report)
            return False
        if reconnected:
            self._register_hub_listeners()
        self.set_connection_status(report=report)
        if cams:
            LOGGER.debug(f'{self.lpfx} Updating cams... {cams}')
            for cam in self.list_cameras():
                if cam['id'] in self.cams_by_id:
                    self.cams_by_id[cam['id']].update_status(cam)
            # list_cameras failure clears camect; refresh ST if so
            if self.camect is False:
                self.set_connection_status(report=report)
                return False
        return True

    def shortPoll(self):
        # We have to update camera status on because there are no callbacks
        # for streaming, but disabled for now to reduce traffic.
        self.update_status(cams=True,report=True)

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
        LOGGER.info(f'{self.lpfx}: Adding saved cameras...')
        for cam in self.controller.get_saved_cameras(self):
            LOGGER.debug(f"{self.lpfx}: Adding cam {cam['node_address']} {cam['name']}")
            ccam = self.list_camera(cam['id'])
            if ccam is None:
                LOGGER.error(f"{self.lpfx}: Saved camera is no longer listed in this Hub: {cam}")
                self.controller.remove_stale_camera(cam)
                continue
            self._add_camera_node(cam, ccam)

    def discover(self):
        LOGGER.info('started')
        for cam in self.list_cameras():
            LOGGER.debug(f"{self.lpfx}: Check camera: {cam}")
            if not cam['disabled']:
                self.add_camera(cam)
        LOGGER.info('completed')

    def get_and_add_camera(self,camid):
        cam = self.list_camera(camid)
        if cam is not None:
            self.add_camera(cam)

    def _add_camera_node(self, cam_saved, ccam):
        address = cam_saved['node_address']
        if self.controller.poly.getNode(address):
            camera = Camera(self.controller, self, address, ccam)
            self.cams_by_id[cam_saved['id']] = camera
            camera.activate()
        else:
            self.cams_by_id[cam_saved['id']] = self.controller.add_node(
                address, Camera(self.controller, self, address, ccam))

    def add_camera(self,cam):
        if cam is None:
            return
        cam_address = self.controller.get_cam_address(cam,self)
        LOGGER.debug(f"Adding cam {cam_address} {cam['name']}")
        if cam['id'] in self.cams_by_id:
            self.cams_by_id[cam['id']].update_status(cam)
            return
        if self.controller.poly.getNode(cam_address):
            camera = Camera(self.controller, self, cam_address, cam)
            self.cams_by_id[cam['id']] = camera
            camera.activate()
        else:
            self.cams_by_id[cam['id']] = self.controller.add_node(
                cam_address, Camera(self.controller, self, cam_address, cam))

    def enable_alert(self, cam_id):
        LOGGER.info(f"{self.lpfx}: {cam_id}")
        return self.camect.enable_alert([cam_id],"nodeserver")

    def disable_alert(self, cam_id):
        LOGGER.info(f"{self.lpfx}: {cam_id}")
        return self.camect.disable_alert([cam_id],"nodeserver")

    def delete(self):
        LOGGER.info(f'{self.lpfx}: Host deleted, removing hub data')
        for hub_id, hub_info in list(self.controller.saved_data.items()):
            if hub_info.get('type') == 'hub' and hub_info.get('node_address') == self.address:
                self.controller.remove_hub(hub_id)
                return

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def cmd_set_mode(self,command):
        LOGGER.debug(f'{self.lpfx}: {command}')
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
