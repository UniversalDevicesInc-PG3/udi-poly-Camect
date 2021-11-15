
from udi_interface import Node,LOG_HANDLER,LOGGER,Custom
import logging,time,json
import camect

# My Nodea
from nodes import Host
from const import HOST_MODE_MAP,NODE_DEF_MAP

# IF you want a different log format than the current default
#LOG_HANDLER.set_log_format('%(asctime)s %(threadName)-10s %(name)-18s %(levelname)-8s %(module)s:%(funcName)s: %(message)s')

class CamectController(Node):
    def __init__(self, polyglot, primary, address, name):
        super(CamectController, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = 'Camect Controller'
        self.hb = 0
        self.nodes_by_id = {}
        self.hosts = None
        self.saved_hosts = None
        self.saved_cameras = None
        self.next_host = None
        self.next_cam = None
        self.in_discover = False
        self.hosts_connected = 0
        self.config_st = False # Configuration good?
        # Cross reference of host and camera id's to their node.
        self.__modifiedCustomData = False
        self.__my_drivers = {}
        # Flags to know when all these are processed
        self.dataHandler_done = False
        self.paramHandler_done = False
        self.typedDataHandler_done = False
        self.start_done = False
        self.customData = Custom(polyglot, 'customdata')
        polyglot.subscribe(polyglot.START,           self.start, address)
        polyglot.subscribe(polyglot.CUSTOMPARAMS,    self.parameterHandler)
        polyglot.subscribe(polyglot.CUSTOMDATA,      self.dataHandler)
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.typedDataHandler)
        polyglot.subscribe(polyglot.POLL,            self.poll)

        polyglot.ready()
        polyglot.addNode(self)

        self.TypedParams = Custom(polyglot, 'customtypedparams')
        self.TypedParams.load(
            [
                {
                    'name': 'hosts',
                    'title': 'Camect Host',
                    'desc': 'Camect Hosts',
                    'isList': True,
                    'params': [
                        {
                            'name': 'host',
                            'title': 'Camect Host or IP Address',
                            'isRequired': True,
                            'defaultValue': ['camect.local']
                        },
                    ]
                },
            ],
            True
        )
            

    def dataHandler(self, data):
        LOGGER.debug("Enter config={}".format(data))
        self.customData.load(data)
        #self.customData = self.polyConfig['customData']
        self.saved_cameras = self.customData.get('saved_cameras',{})
        self.saved_hosts   = self.customData.get('saved_hosts',{})
        self.next_host     = self.customData.get('next_host',1)
        self.next_cam      = self.customData.get('next_cam',{})
        LOGGER.debug(self.customData)
        LOGGER.warning('saved_hosts={self.saved_hosts}')
        LOGGER.debug(self.next_cam)
        self.dataHandler_done = True
        LOGGER.debug("Exit")

    def parameterHandler(self, params):
        self.poly.Notices.clear()

        if 'user' in params:
            self.user = params['user']
        else:
            LOGGER.error('Custom Parameters: "user" not defined in customParams, please add it.')

        if 'password' in params:
            self.password = params['password']
        else:
            LOGGER.error('Custom Parameters: "password" not defined in customParams, please add it.')

        # Add a notice if they need to change the user/password from the default.
        if self.user == "":
            self.poly.Notices['user'] = 'Please set a proper user.'
        if self.password == "":
            self.poly.Notices['pass'] = 'Please set a proper password.'

        self.paramHandler_done = True
        if self.user != "" and self.password != "":
            self.discover()

    def typedDataHandler(self, typed_data):
        LOGGER.debug("Enter config={}".format(typed_data))
        self.hosts = typed_data['hosts']
        self.set_hosts_configured()
        self.typedDataHandler_done = True
        self.discover()

    def start(self):
        LOGGER.info('Started Camect NodeServer {}'.format(self.poly.serverdata['version']))
        self.set_driver('ST', 1)
        self.set_hosts_configured()
        self.set_hosts_connected()
        self.heartbeat()
        self.start_done = True
        #self.set_debug_level()
        self.discover()
        LOGGER.debug('done')

    def save_custom_data(self,force=False):
        if self.__modifiedCustomData or force:
            LOGGER.debug("saving")
            self.customData['saved_cameras'] = self.saved_cameras
            self.customData['saved_hosts']   = self.saved_hosts
            self.customData['next_host']     = self.next_host
            self.customData['next_cam']      = self.next_cam
            #self.saveCustomData(self.customData)
            self.__modifiedCustomData = False
        #else:
        #    LOGGER.debug("No save necessary")

    def poll(self, polltype):
        if 'shortPoll' in polltype:
            LOGGER.debug('')
            self.save_custom_data()
            self.set_hosts_connected()
            # Call shortpoll on the camect hosts
            for id,node in self.nodes_by_id.items():
                node.shortPoll()
        else:
            LOGGER.debug('')
            self.heartbeat()

    def query(self,command=None):
        self.check_params()
        # Call shortpoll on the camect hosts
        for id,node in self.nodes_by_id.items():
            node.query()

    def heartbeat(self):
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def set_mode_by_name(self,mname):
        LOGGER.debug(f'mode={mname}')
        if mname in HOST_MODE_MAP:
            self.set_mode(HOST_MODE_MAP[mname])
            return
        LOGGER.error(f'Unknown Host Mode Name "{mname}"')

    def set_mode(self,val=None):
        LOGGER.debug(f'val={val}')
        if val is None:
            val = self.get_driver('MODE')
        self.set_driver('MODE',val)

    def set_mode_all(self):
        """
        Updates the controller host mode based on all host modes
        Called at startup and when any host node changes modes.
        """
        hmode = None
        for id,node in self.nodes_by_id.items():
            tmode = node.camect.get_mode()
            LOGGER.debug(f'{node.name} MODE={tmode}')
            if hmode is None:
                hmode = tmode
            elif hmode != tmode:
                hmode = 'MIXED'
            LOGGER.debug(f'MODE={hmode}')
        if hmode is not None:
            self.set_mode_by_name(hmode)

    def discover(self):
        if self.config_st:
            LOGGER.warning("discover can't run until config params are set...")
            return
        if self.in_discover:
            LOGGER.warning("discover already running.")
            return
        self.in_discover = True
        LOGGER.info(f'starting')
        while not (self.start_done and self.paramHandler_done and self.typedDataHandler_done and self.dataHandler_done):
            LOGGER.warning(f'waiting for start_done {self.start_done} and paramHandler_done {self.paramHandler_done} and typedDataHandler_done {self.typedDataHandler_done} and dataHandler_done {self.dataHandler_done}')
            time.sleep(1)
        LOGGER.warning(f'start_done={self.start_done} and paramHandler_done={self.paramHandler_done} and typedDataHandler_done={self.typedDataHandler_done} and dataHandler_done={self.dataHandler_done}')
        if self.hosts is None:
            LOGGER.warning("No hosts configured...")
        else:
            LOGGER.debug(f'saved_hosts={json.dumps(self.saved_hosts,indent=2)}')
            LOGGER.debug(f'saved_cameras={json.dumps(self.saved_cameras,indent=2)}')
            for host in self.hosts:
                # Would be better to do this conneciton inside the Host object
                # but addNode is async so we ned to get the address in this loop
                # before addNode is called :()
                camect_obj = self.connect_host(host['host'])
                if camect_obj is not False:
                    camect_info = camect_obj.get_info()
                    LOGGER.debug(f"saved_hosts={self.saved_hosts}")
                    if camect_info['id'] in self.saved_hosts:
                        # Use existing and don't re-discover
                        new = False
                        address = self.saved_hosts[camect_info['id']]['node_address']
                    else:
                        # Need to discover
                        new = True
                        address = self.controller.get_host_address(camect_info)
                    try:
                        if not self.poly.getNode(host['host']):
                            self.nodes_by_id[camect_info['id']] = Host(self.poly, address, host['host'], camect_obj, new=new)
                            self.poly.addNode(self.nodes_by_id[camect_info['id']])
                    except:
                        LOGGER.error('Failed to add camect host {host}',exc_info=True)
        self.in_discover = False

        self.save_custom_data()

        if self.hosts is None:
            self.set_driver('GV2',0)
        else:
            self.set_driver('GV2',len(self.hosts))

        self.set_mode_all()

        LOGGER.info('completed')

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def reconnect_host(self,host):
        self.hosts_connected -= 1
        self.set_hosts_connected()
        return self.connect_host(host)

    def connect_host(self,host):
        LOGGER.info(f'Connecting to {host}...')
        try:
            camect_obj = camect.Home(f"{host}:443", self.user, self.password)
        except:
            LOGGER.error(f'Failed to connect to camect host {host}',exc_info=True)
            return False
        self.hosts_connected += 1
        self.set_hosts_connected()
        LOGGER.info(f'Camect Name={camect_obj.get_name()}')
        LOGGER.debug(f'Camect Info={camect_obj.get_info()}')
        return camect_obj

    def get_cam_address(self,icam,parent):
        """
        Given a camera dict from Camect API return it's address if saved or generate new address
        Does not update customData, so customData must be saved by controller if this is modified.
        """
        if icam['id'] in self.saved_cameras:
            nc = self.saved_cameras[icam['id']]['node_address']
            LOGGER.debug(f"exsting camera for {parent.address} {nc} name={icam['name']} saved_name={self.saved_cameras[icam['id']]['name']}")
            return nc
        # Stored by parent adress
        nc = self.next_cam.get(parent.address,1)
        self.next_cam[parent.address] = nc + 1
        icam['node_address'] = f'{parent.address}_{nc:03d}'
        icam['parent_address'] = parent.address
        LOGGER.debug(f"append new camera for {parent.address} {icam['node_address']}: {icam}")
        self.saved_cameras[icam['id']] = icam
        self.__modifiedCustomData = True
        return icam['node_address']   

    def get_saved_cameras(self,parent):
        ret = []
        for camid, cam in self.saved_cameras.items():
            if cam['parent_address'] == parent.address:
                ret.append(cam)
        return ret

    def get_host_address(self,ihost):
        """
        Given a host dict from Camect API return it's address if saved or generate new address
        Does not update customData, so customData must be saved by if this is modified.
        """
        if ihost['id'] in self.saved_hosts:
            nh = self.saved_hosts[ihost['id']]
            LOGGER.debug(f'existing host {hc}')
            return nh
        ihost['node_address'] = f'{self.next_host:02d}'
        self.next_host += 1
        LOGGER.debug(f"append new host: {ihost['node_address']}: {ihost}")
        self.saved_hosts[ihost['id']] = ihost
        self.__modifiedCustomData = True
        return ihost['node_address']   

    def set_hosts_configured(self):
        if self.hosts is None:
            self.set_driver('GV2',0)
        else:
            self.set_driver('GV2',len(self.hosts))

    def set_hosts_connected(self):
        self.set_driver('GV3', self.hosts_connected)

    def set_module_logs(self,level):
        logging.getLogger('urllib3').setLevel(level)

    """
    Create our own get/set driver methods because getDriver from Polyglot can be
    delayed, we sometimes need to know the value before the DB is updated
    and Polyglot gets the update back.
    """
    def set_driver(self,mdrv,val,default=0,force=False,report=True):
        #LOGGER.debug(f'{mdrv},{val} default={default} force={force},report={report}')
        if val is None:
            # Restore from DB for existing nodes
            try:
                val = self.getDriver(mdrv)
                LOGGER.info(f'{val}')
            except:
                LOGGER.warning(f'getDriver({mdrv}) failed which can happen on new nodes, using {default}')
        val = default if val is None else int(val)
        try:
            if not mdrv in self.__my_drivers or val != self.__my_drivers[mdrv] or force:
                self.setDriver(mdrv,val,report=report)
                info = ''
                if self.id in NODE_DEF_MAP and mdrv in NODE_DEF_MAP[self.id]:
                    info += f"'{NODE_DEF_MAP[self.id][mdrv]['name']}' = "
                    info += f"'{NODE_DEF_MAP[self.id][mdrv]['keys'][val]}'" if val in NODE_DEF_MAP[self.id][mdrv]['keys'] else "'NOT IN NODE_DEF_MAP'"            
                self.__my_drivers[mdrv] = val
                LOGGER.debug(f'set_driver({mdrv},{val}) {info}')
            #else:
            #    LOGGER.debug(f'not necessary')
        except:
            LOGGER.error(f'set_driver({mdrv},{val}) failed',exc_info=True)
            return None
        return val

    def get_driver(self,mdrv):
        return self.__my_drivers[mdrv] if mdrv in self.__my_drivers else None

    def cmd_discover(self,command):
        LOGGER.info('')
        self.discover()

    def cmd_set_debug_mode(self,command):
        val = int(command.get('value'))
        LOGGER.debug("cmd_set_debug_mode: {}".format(val))
        self.set_debug_level(val)

    def cmd_set_mode(self,command):
        for id,node in self.nodes_by_id.items():
            node.cmd_set_mode(command)

    id = 'controller'
    commands = {
        'QUERY': query,
        'DISCOVER': cmd_discover,
        'SET_DM': cmd_set_debug_mode,
        'SET_MODE': cmd_set_mode
}
    drivers = [
        {'driver': 'ST',   'value':  1, 'uom': 2}, 
        {'driver': 'MODE', 'value':  0, 'uom': 25}, # Host Mode of all Hosts
        {'driver': 'GV2',  'value':  0, 'uom': 25}, # Camects Configured
        {'driver': 'GV3',  'value':  0, 'uom': 25}, # Camects Connected
    ]
