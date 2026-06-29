

import sys,os,hashlib,re

def myint(value):
    """ round and convert to int """
    return int(round(float(value)))

def myfloat(value, prec=4):
    """ round and return float """
    return round(float(value), prec)

def ip2long(ip):
    """ Convert an IP string to long """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]

def long2ip(value):
    return socket.inet_ntoa(struct.pack('!L', value))

def uuid_to_address(uuid):
    return uuid[-12:]

def id_to_address(id,slen=14):
    slen = slen * -1
    m = hashlib.md5()
    m.update(id.encode())
    return m.hexdigest()[slen:]

def get_valid_node_name(name):
    # Only allow utf-8 characters
    #  https://stackoverflow.com/questions/26541968/delete-every-non-utf-8-symbols-froms-string
    name = bytes(name, 'utf-8').decode('utf-8','ignore')
    # Remove <>`~!@#$%^&*(){}[]?/\;:"'` characters from name
    return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", name)

def get_valid_node_address(name):
    return get_valid_node_name(name)[:14].lower()

def parse_host_port(host_entry, default_port='443'):
    """Return hostname and port from typed host config or host:port string."""
    if isinstance(host_entry, str):
        host = host_entry
        port = default_port
    else:
        host = host_entry.get('host', '')
        port = str(host_entry.get('port') or default_port)
    host = host.strip()
    if host.startswith('['):
        if ']:' in host:
            h, p = host.rsplit(':', 1)
            host = h + ']'
            if p.isdigit():
                port = p
    elif host.count(':') == 1:
        h, p = host.rsplit(':', 1)
        if p.isdigit():
            host = h
            port = p
    return host, port
