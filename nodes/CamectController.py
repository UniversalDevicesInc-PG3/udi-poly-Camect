
from udi_interface import Node,LOG_HANDLER,LOGGER,Custom
import logging,time,json
import camect

# My Nodea
from nodes import Host
from const import HOST_MODE_MAP,NODE_DEF_MAP,DETECTED_OBJECT_MAP
from node_funcs import parse_host_port

# IF you want a different log format than the current default
#LOG_HANDLER.set_log_format('%(asctime)s %(threadName)-10s %(name)-18s %(levelname)-8s %(module)s:%(funcName)s: %(message)s')

class CamectController(Node):
    def __init__(self, poly, primary, address, name):
        super(CamectController, self).__init__(poly, primary, address, name)
        self.poly = poly
        self.name = 'Camect Controller'
        self.hb = 0
        self.n_queue = []
        self.nodes_by_id = {}
        self.hosts = None
        self.saved_data = {}
        # Stores the last camera number by parent.address
        self.last_cam_num = {}
        self.in_discover = False
        self.hosts_connected = 0
        self.user = ''
        self.password = ''
        # Cross reference of host and camera id's to their node.
        self.__modifiedCustomData = False
        self.__my_drivers = {}
        # Flags to know when all these are processed
        self.configHandler_st = False
        self.dataHandler_done = False
        self.paramHandler_done = False
        self.typedDataHandler_done = False
        self.start_done = False
        self.Params     = Custom(poly, 'customparams')
        poly.subscribe(poly.START,           self.start, address)
        poly.subscribe(poly.CUSTOMPARAMS,    self.parameterHandler)
        poly.subscribe(poly.CUSTOMNS,        self.customNS_handler)
        poly.subscribe(poly.CUSTOMTYPEDDATA, self.typedDataHandler)
        poly.subscribe(poly.POLL,            self.poll)
        poly.subscribe(poly.DISCOVER,        self.discover)
        poly.subscribe(poly.ADDNODEDONE,     self.node_queue)
        poly.subscribe(poly.CONFIGDONE,      self.handler_config_done)
        poly.subscribe(poly.LOGLEVEL,        self.handler_log_level)

        poly.ready()
        poly.addNode(self, conn_status="ST")

        self.Notices         = Custom(poly, 'notices')
        self.TypedData       = Custom(poly, 'customtypeddata')
        self.TypedParams     = Custom(poly, 'customtypedparams')
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
                        {
                            'name': 'port',
                            'title': 'Port',
                            'isRequired': False,
                            'defaultValue': ['443']
                        },
                    ]
                },
            ],
            True
        )

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_queue(self, data):
        self.n_queue.append(data['address'])
        # Start up ELK connection when controller node is all done being added.
        if (data['address'] == self.address):
            self.add_node_done()


    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def add_node(self,address,node):
        # See if we need to check for node name changes where ELK is the source
        cname = self.poly.getNodeNameFromDb(address)
        if cname is not None:
            LOGGER.debug(f"node {address} Requested: '{node.name}' Current: '{cname}'")
            # Check that the name matches
            if node.name != cname:
                if self.Params['change_node_names'] == 'true':
                    LOGGER.warning(f"Existing node name '{cname}' for {address} does not match requested name '{node.name}', changing to match")
                    self.poly.renameNode(address,node.name)
                else:
                    LOGGER.warning(f"Existing node name '{cname}' for {address} does not match requested name '{node.name}', NOT changing to match, set change_node_names=true to enable")
                    # Change it to existing name to avoid addNode error
                    node.name = cname
        LOGGER.debug(f"Adding: {node.name}")
        self.poly.addNode(node)
        self.wait_for_node_done()
        gnode = self.poly.getNode(address)
        if gnode is None:
            LOGGER.error('Failed to add node address')
        return node

    def add_node_done(self):
        LOGGER.debug("start")
        if self.user != "" and self.password != "":
            self.discover()
        LOGGER.debug("done")

    def parameterHandler(self,data):
        LOGGER.debug("Enter data={}".format(data))
        # Our defaults, make sure the exist in case user deletes one
        params = {
            'user': '',
            'password': "",
            'change_node_names': "false"
        }
        if data is not None:
            # Load what we have
           self.Params.load(data)

        # Assume we are good unless something bad is found
        st = True

        # Make sure all the params exist.
        for param in params:
            if data is None or not param in data:
                LOGGER.error(f'Add back missing param {param}')
                self.Params[param] = params[param]
                # Can't do anything else because we will be called again due to param change
                return

        # Make sure they all have a value that is not the default
        for param in params:
            if data[param] == "" or (data[param] == params[param] and param != "change_node_names"):
                msg = f'Please define {param}'
                LOGGER.error(msg)
                self.Notices[param] = msg
                st = False
            else:
                self.Notices.delete(param)

        self.user     = self.Params['user']
        self.password = self.Params['password']

        self.paramHandler_done = st

        LOGGER.debug(f'exit: {self.paramHandler_done}')

    def typedDataHandler(self, typed_data):
        LOGGER.debug("Enter config={}".format(typed_data))
        self.TypedData.load(typed_data)
        self.hosts = self.TypedData['hosts']
        self.set_hosts_configured()
        self.typedDataHandler_done = True
        self.discover()

    def start(self):
        LOGGER.info('Started Camect NodeServer {}'.format(self.poly.serverdata['version']))
        self.set_driver('ST', 1)
        self.set_hosts_configured()
        self.set_hosts_connected()
        self.heartbeat()
        # Due to a bug in current version of ISY 5.4.4 when we send Status, it triggers a 
        # Control program so we only send status if it's on.  We also can't send the off 
        # since that triggers it as well.
        self.has_st_bug = True if self.poly.pg3init['isyVersion'] == "5.4.4" or self.poly.pg3init['isyVersion'] == "5.3.4" else False
        LOGGER.warning(f"This ISY {self.poly.pg3init['isyVersion']} has_st_bug={self.has_st_bug}")
        self.start_done = True
        #self.set_debug_level()
        self.discover()
        LOGGER.debug('done')

    def poll(self, polltype):
        if 'shortPoll' in polltype:
            LOGGER.debug('')
            self.set_hosts_connected()
            # Call shortpoll on the camect hosts
            for id,node in self.nodes_by_id.items():
                node.shortPoll()
        else:
            LOGGER.debug('')
            self.heartbeat()

    def handler_config_done(self):
        LOGGER.debug('enter')
        self.poly.addLogLevel('DEBUG_MODULES',9,'Debug + Modules')
        self.handler_config_st = True
        LOGGER.debug('exit')

    def handler_log_level(self,level):
        LOGGER.info(f'enter: level={level}')
        if level['level'] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            LOG_HANDLER.set_basic_config(True,logging.DEBUG)
        else:
            LOGGER.info("Setting basic config to WARNING...")
            LOG_HANDLER.set_basic_config(True,logging.WARNING)
        LOGGER.info(f'exit: level={level}')

    def query(self,command=None):
        self.set_hosts_configured()
        self.set_hosts_connected()
        self.reportDrivers()

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
            if node.camect is False:
                continue
            try:
                tmode = node.camect.get_mode()
            except Exception:
                LOGGER.error(f'{node.name} failed to get mode', exc_info=True)
                continue
            LOGGER.debug(f'{node.name} MODE={tmode}')
            if hmode is None:
                hmode = tmode
            elif hmode != tmode:
                hmode = 'MIXED'
            LOGGER.debug(f'MODE={hmode}')
        if hmode is not None:
            self.set_mode_by_name(hmode)

    def customNS_handler(self, key, idata):
        LOGGER.debug(f"Enter key={key} data={idata}")
        # We don't care about oauth
        if key == 'oauth':
            return
        if not key in idata:
            LOGGER.error(f"Got key={key} which is not in data={idata}")
            return
        # Why does it send the key and the key'ed data?
        data = idata[key]
        #self.customData.load(data)
        self.saved_data[key] = data
        if data['type'] == 'cam':
            last_num = self.last_cam_num.get(data['parent_address'],0)
            if data['num'] > last_num:
                self.last_cam_num[data['parent_address']] = data['num']
        LOGGER.debug(f'last_cam_num = {self.last_cam_num}')
        self.dataHandler_done = True


    def get_saved_hub(self,camect_info):
        LOGGER.debug(f"camect_info={camect_info}")
        ret = self.saved_data.get(camect_info['id'],None)
        LOGGER.debug(f"got={ret}")
        return ret
    
    def add_saved_hub(self,camect_info, host, port):
        id = camect_info['id']
        LOGGER.debug(f"camect_info={camect_info}")
        hub_num = self.next_hub_num()
        ihost = {
            'type':         'hub',
            'name':         camect_info['name'],
            'num':          hub_num,
            'node_address': f'{hub_num:02d}',
            'host':         host,
            'port':         port,
        }
        LOGGER.debug(f"append new host: {ihost['node_address']}: {ihost}")
        self.saved_data[id] = ihost
        custom = Custom(self.poly,id)
        custom[id] = ihost
        return ihost

    def next_hub_num(self):
        last_hub = 0
        for key,data in self.saved_data.items():
            if data['type'] == 'hub':
                last_hub = int(data['num'])
        return last_hub + 1

    def get_saved_cam(self,icam):
        return self.saved_data.get(icam['id'],None)

    def get_saved_cameras(self,parent):
        ret = []
        for camid, cam in self.saved_data.items():
            if cam['type'] == 'cam' and cam['parent_address'] == parent.address:
                ret.append(cam)
        return ret

    def add_saved_cam(self,icam,parent):
        ncn = self.next_cam_num(parent.address)
        icam['type'] = 'cam'
        icam['num']  = ncn
        icam['node_address'] = f'{parent.address}_{ncn:03d}'
        icam['parent_address'] = parent.address
        LOGGER.debug(f"append new camera for {parent.address} {icam['node_address']}: {icam}")
        self.saved_data[icam['id']] = icam
        custom = Custom(self.poly,icam['id'])
        custom[icam['id']] = icam
        return icam

    def next_cam_num(self,parent_address):
        nc = self.last_cam_num.get(parent_address,0) + 1
        self.last_cam_num[parent_address] = nc
        return nc

    def get_cam_address(self,icam,parent):
        """
        Given a camera dict from Camect API return it's address if saved or 
        generate new address and save it
        """
        if icam['id'] in self.saved_data:
            address = self.saved_data[icam['id']]['node_address']
            LOGGER.debug(f"exsting camera for {parent.address} {address} name={icam['name']} saved_name={self.saved_data[icam['id']]['name']}")
            return address
        # Stored by parent adress
        return self.add_saved_cam(icam,parent)['node_address']

    def configured_endpoints(self):
        endpoints = set()
        if self.hosts is None:
            return endpoints
        for host_entry in self.hosts:
            host, port = parse_host_port(host_entry)
            endpoints.add((host.lower(), port))
        return endpoints

    def remove_stale_camera(self, cam_saved):
        cam_id = cam_saved['id']
        address = cam_saved['node_address']
        LOGGER.warning(f'Removing stale camera {address} ({cam_saved.get("name", cam_id)})')
        for cat in DETECTED_OBJECT_MAP:
            child_addr = f'{address}_{cat}'[:14]
            if self.poly.getNode(child_addr):
                self.poly.delNode(child_addr)
        if self.poly.getNode(address):
            self.poly.delNode(address)
        for host in self.nodes_by_id.values():
            if cam_id in host.cams_by_id:
                del host.cams_by_id[cam_id]
        if cam_id in self.saved_data:
            del self.saved_data[cam_id]
        custom = Custom(self.poly, cam_id)
        custom.delete(cam_id)

    def remove_hub(self, hub_id):
        hub_info = self.saved_data.get(hub_id)
        if hub_info is None:
            return
        address = hub_info['node_address']
        LOGGER.warning(f'Removing hub {address} ({hub_info.get("name", hub_id)})')
        for camid, cam in list(self.saved_data.items()):
            if cam.get('type') == 'cam' and cam.get('parent_address') == address:
                self.remove_stale_camera(cam)
        if hub_id in self.nodes_by_id:
            del self.nodes_by_id[hub_id]
        if self.poly.getNode(address):
            self.poly.delNode(address)
        if hub_id in self.saved_data:
            del self.saved_data[hub_id]
        custom = Custom(self.poly, hub_id)
        custom.delete(hub_id)

    def remove_orphan_hubs(self):
        if self.hosts is None or len(self.hosts) == 0:
            for hub_id, hub_info in list(self.saved_data.items()):
                if hub_info.get('type') == 'hub':
                    self.remove_hub(hub_id)
            return
        configured = self.configured_endpoints()
        for hub_id, hub_info in list(self.saved_data.items()):
            if hub_info.get('type') != 'hub':
                continue
            host = hub_info.get('host')
            if not host:
                continue
            endpoint = (host.lower(), str(hub_info.get('port', '443')))
            if endpoint not in configured:
                LOGGER.warning(f'Hub {hub_info.get("name")} ({endpoint[0]}:{endpoint[1]}) no longer configured, removing')
                self.remove_hub(hub_id)

    def ensure_host(self, host_entry, camect_obj, camect_info):
        host, port = parse_host_port(host_entry)
        hub_info = self.get_saved_hub(camect_info)
        if hub_info is None:
            new = True
            hub_info = self.add_saved_hub(camect_info, host, port)
        else:
            new = False
            hub_info['host'] = host
            hub_info['port'] = port
            self.saved_data[camect_info['id']] = hub_info
            custom = Custom(self.poly, camect_info['id'])
            custom[camect_info['id']] = hub_info

        hub_id = camect_info['id']
        if hub_id in self.nodes_by_id:
            self.nodes_by_id[hub_id].camect = camect_obj
            self.nodes_by_id[hub_id].host = host
            self.nodes_by_id[hub_id].port = port
            return

        hub_address = hub_info['node_address']
        host_node = Host(self, hub_address, host, port, camect_obj, new)
        if self.poly.getNode(hub_address):
            self.nodes_by_id[hub_id] = host_node
            host_node.activate()
        else:
            self.nodes_by_id[hub_id] = host_node
            self.add_node(hub_address, host_node)

    def discover(self):
        if not self.user or not self.password:
            LOGGER.warning("discover skipped until credentials are configured")
            return
        if self.in_discover:
            LOGGER.warning("discover already running.")
            return
        self.in_discover = True
        LOGGER.info('starting')
        self.hosts_connected = 0
        self.remove_orphan_hubs()
        if self.hosts is None:
            LOGGER.warning("No hosts configured...")
        else:
            for host_entry in self.hosts:
                host, port = parse_host_port(host_entry)
                camect_obj = self.connect_host(host, port)
                if camect_obj is not False:
                    try:
                        camect_info = camect_obj.get_info()
                        self.ensure_host(host_entry, camect_obj, camect_info)
                    except Exception:
                        LOGGER.error(f'Failed to add camect host {host}:{port}', exc_info=True)
        self.in_discover = False
        LOGGER.info('done')

        self.set_hosts_configured()
        self.set_mode_all()

        LOGGER.info('completed')

    def delete(self):
        LOGGER.info('Camect controller deleted, removing configured hubs')
        for hub_id in list(self.nodes_by_id.keys()):
            self.remove_hub(hub_id)

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def reconnect_host(self, host, port='443'):
        return self.connect_host(host, port, increment=False)

    def connect_notice_key(self, host, port):
        return f'connect_{host}:{port}'

    def connect_host(self, host, port='443', increment=True):
        LOGGER.info(f'Connecting to {host}:{port}...')
        notice_key = self.connect_notice_key(host, port)
        try:
            camect_obj = camect.Home(f"{host}:{port}", self.user, self.password)
        except Exception as err:
            msg = f'Failed to connect to Camect at {host}:{port}: {err}'
            LOGGER.error(msg, exc_info=True)
            self.Notices[notice_key] = msg
            return False
        self.Notices.delete(notice_key)
        if increment:
            self.hosts_connected += 1
        self.set_hosts_connected()
        LOGGER.info(f'Camect Name={camect_obj.get_name()}')
        LOGGER.debug(f'Camect Info={camect_obj.get_info()}')
        return camect_obj

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
        {'driver': 'ST',   'value':  1, 'uom': 25}, 
        {'driver': 'MODE', 'value':  0, 'uom': 25}, # Host Mode of all Hosts
        {'driver': 'GV2',  'value':  0, 'uom': 25}, # Camects Configured
        {'driver': 'GV3',  'value':  0, 'uom': 25}, # Camects Connected
    ]
