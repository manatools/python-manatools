# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.services contains systemd services backend

This module aims to share all the API to manage system services,
to be used from GUI applications or console.

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package mamatools.services
'''

import dbus
import os.path

class Services() :
    '''
    Services provides an easy access to systemd services
    '''
    def __init__(self):
        '''
        Services constructor
        '''
        self._bus = dbus.SystemBus()
        self._systemd = self._bus.get_object('org.freedesktop.systemd1',
                                 '/org/freedesktop/systemd1')
        self.include_static_services = False
        self._reload = True
        self._services = {}
    
    @property    
    def service_info(self):
        '''
        A dictionary collecting all the service information.
        if include_static_services (default is false) is set also static
        services are included.
        '''
        if not self._reload :
            return self._services
        
        manager = dbus.Interface(self._systemd, dbus_interface='org.freedesktop.systemd1.Manager')
        units = manager.ListUnits()
        self._services = {}
        self._reload = False
        
        for u in units:
            unitName = u[0] #### name
            pos = unitName.find(".service")
            if pos != -1 :
                try:
                    if unitName.find("@") == -1 :
                        st = manager.GetUnitFileState(unitName)
                        name = unitName[0:pos]
                        if st and (self.include_static_services or st != 'static'):
                            self._services[name] = {
                                'name':        u[0],
                                'description': u[1],
                                'load_state':  u[2],
                                'active_state':u[3],
                                'sub_state':   u[4],
                                'unit_path':   u[6],
                                'enabled'  :   st == 'enabled',
                            }
                        # TODO if not st check unit files see Services.pm:167
                except: 
                    pass   
        
        unit_files = manager.ListUnitFiles()
        for u in unit_files:
            unitName = u[0]
            st = u[1]
            pos = unitName.find(".service")
            if pos != -1 :
                name = os.path.basename(unitName)
                name = name[0:name.find(".service")]
                if (not name in self._services.keys()) and (name.find('@') == -1) \
                    and (os.path.isfile(unitName) or os.path.isfile("/etc/rc.d/init.d/"+name)) \
                        and not os.path.islink(unitName) and (st == "disabled" or st == "enabled"):
                    self._services[name] = {
                                'name':        name+".service",
                                #'description': ####TODO get property,
                                'description': "---",
                                'enabled'  :   st == 'enabled',
                            }
 
        return self._services
