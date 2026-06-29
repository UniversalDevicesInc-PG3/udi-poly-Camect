
NODE_DEF_MAP = {

}

HOST_MODE_MAP = {
    'MIXED':  -1,
    'DEFAULT': 0,
    'HOME':    1,
}

DETECTED_OBJECT_MAP = {
    'human': {
        'Santa Claus':              { 'num': 0,  'name': 'Santa Claus' },
        'person':                   { 'num': 1,  'name': 'Person' },
        'Amazon person':            { 'num': 2,  'name': 'Amazon' },
        'DHL person':               { 'num': 3,  'name': 'DHL' },
        'DPD person':               { 'num': 4,  'name': 'DPD' },
        'FedEx person':             { 'num': 5,  'name': 'FedEx' },
        'RoyalMail person':         { 'num': 6,  'name': 'Royal Mail' },
        'UPS person':               { 'num': 7,  'name': 'UPS' },
        'USPS person':              { 'num': 8,  'name': 'USPS' },
    },

    'vehicle': {
        'Amazon':                   { 'num': 0,  'name': 'Amazon' },
        'Amazon truck':             { 'num': 0,  'name': 'Amazon' },
        'Amazon car':               { 'num': 0,  'name': 'Amazon' },
        'Amazon pickup':            { 'num': 0,  'name': 'Amazon' },
        'DHL':                      { 'num': 1,  'name': 'DHL' },
        'DHL truck':                { 'num': 1,  'name': 'DHL' },
        'DHL car':                  { 'num': 1,  'name': 'DHL' },
        'DHL pickup':               { 'num': 1,  'name': 'DHL' },
        'FedEx':                    { 'num': 2,  'name': 'FedEx' },
        'FedEx truck':              { 'num': 2,  'name': 'FedEx' },
        'FedEx car':                { 'num': 2,  'name': 'FedEx' },
        'FedEx pickup':             { 'num': 2,  'name': 'FedEx' },
        'RoyalMail':                { 'num': 3,  'name': 'Royal Mail' },
        'RoyalMail truck':          { 'num': 3,  'name': 'Royal Mail' },
        'RoyalMail car':            { 'num': 3,  'name': 'Royal Mail' },
        'RoyalMail pickup':         { 'num': 3,  'name': 'Royal Mail' },
        'UPS':                      { 'num': 4,  'name': 'UPS' },
        'UPS truck':                { 'num': 4,  'name': 'UPS' },
        'UPS car':                  { 'num': 4,  'name': 'UPS' },
        'UPS pickup':               { 'num': 4,  'name': 'UPS' },
        'USPS':                     { 'num': 5,  'name': 'USPS' },
        'USPS truck':               { 'num': 5,  'name': 'USPS' },
        'USPS car':                 { 'num': 5,  'name': 'USPS' },
        'USPS pickup':              { 'num': 5,  'name': 'USPS' },
        'bicycle':                  { 'num': 6,  'name': 'Bicycle' },
        'bus':                      { 'num': 7,  'name': 'Bus' },
        'car':                      { 'num': 8,  'name': 'Car' },
        'motorcycle':               { 'num': 9,  'name': 'Motorcycle' },
        'pickup':                   { 'num': 10, 'name': 'Pickup' },
        'truck':                    { 'num': 11, 'name': 'Truck' },
    },
    'animal': {
        'bear':                     { 'num': 0,  'name': 'Bear' },
        'bird':                     { 'num': 1,  'name': 'Bird' },
        'cat':                      { 'num': 2,  'name': 'Cat' },
        'deer':                     { 'num': 3,  'name': 'Deer' },
        'dog':                      { 'num': 4,  'name': 'Dog' },
        'mouse':                    { 'num': 5,  'name': 'Mouse' },
        'rabbit':                   { 'num': 6,  'name': 'Rabbit' },
        'raccoon':                  { 'num': 7,  'name': 'Raccoon' },
        'skunk':                    { 'num': 8,  'name': 'Skunk' },
        'squirrel':                 { 'num': 9,  'name': 'Squirrel' },
        'unknown animal':           { 'num': 10, 'name': 'Unknown Animal' },
        'unknown small animal':     { 'num': 11, 'name': 'Unknown Small Animal' },
        'fox':                      { 'num': 12, 'name': 'Fox' },
    },
    'insect': {
        'fly':                      { 'num':  0,  'name': 'Fly' },
        'spider':                   { 'num':  1,  'name': 'Spider' },
    },

}

# Camect API object names that differ from DETECTED_OBJECT_MAP keys.
OBJECT_ALIASES = {
    'Amazon truck':             'Amazon',
    'USPS truck':               'USPS',
    'UPS':                      'UPS truck',
    'Royal Mail':               'RoyalMail',
}

def normalize_object_name(name):
    """Map Camect-reported object names to DETECTED_OBJECT_MAP keys."""
    if name in OBJECT_ALIASES:
        name = OBJECT_ALIASES[name]
    for sub in (' truck', ' car', ' pickup'):
        if name.endswith(sub):
            name = name.removesuffix(sub)
    return name
