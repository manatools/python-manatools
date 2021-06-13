# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.services contains systemd services back end

This module aims to share all the API to manage system services,
to be used from GUI applications or console.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.services
'''

from pydbus import SystemBus
import os.path
import subprocess
from sys import stderr


class Services():
    '''
    Services provides an easy access to systemd services
    '''

    def __init__(self):
        '''
        Services constructor
        '''
        self.include_static_services = False
        self._reload = True
        self._services = {}
        self._xinetd_services = {}
        self._bus = SystemBus()
        self._systemd = self._bus.get(".systemd1")
        self._manager = self._systemd[".Manager"]

    def check_permission(action, dbus_context):
        '''
        Check authorizations
        '''
        return dbus_context.is_authorized(action, {'polkit.icon_name': 'manatools.png',}, interactive=True)
    
    @property
    def service_info(self):
        '''
        A dictionary collecting all the service information.
        if include_static_services (default is false) is set also static
        services are included.
        '''
        if not self._reload:
            return self._services
        units = self._manager.ListUnits()
        self._services = {}
        self._reload = False

        for u in units:
            unitName = u[0]
            pos = unitName.find(".service")
            if pos != -1:
                try:
                    if unitName.find("@") == -1:
                        st = self._manager.GetUnitFileState(unitName)
                        name = unitName[0:pos]
                        if st and (self.include_static_services or st != 'static'):
                            self._services[name] = {
                                'name':        u[0],
                                'description': u[1],
                                'load_state':  u[2],
                                'active_state': u[3],
                                'sub_state':   u[4],
                                'unit_path':   u[6],
                                'enabled':   st == 'enabled',
                            }
                            # TODO if not st check unit files see Services.pm:167
                except:
                    pass

        unit_files = self._manager.ListUnitFiles()
        for u in unit_files:
            unitName = u[0]
            st = u[1]
            pos = unitName.find(".service")
            if pos != -1:
                name = os.path.basename(unitName)
                name = name[0:name.find(".service")]
                if (not name in self._services.keys()) and (name.find('@') == -1) \
                   and (os.path.isfile(unitName) or os.path.isfile("/etc/rc.d/init.d/"+name)) \
                   and not os.path.islink(unitName) and (st == "disabled" or st == "enabled"):
                    self._services[name] = {
                        'name':        name+".service",
                        # 'description': ####TODO get property,
                        'description': "---",
                        'enabled':   st == 'enabled',
                    }

        return self._services

    @property
    def xinetd_services(self):
        '''
        This function returns all the xinetd services in the system.
        NOTE that xinetd *must* be enable at boot to get this info
        '''
        try:
            service_info = self.service_info()['xinetd']
            if service_info['enabled']:
                env = {'LANGUAGE': 'C', 'PATH': "/usr/bin:/usr/sbin"}
                # TODO : Change to force root command
                try:
                    chkconf = subprocess.run(['/usr/sbin/chkconfig', '--list', '--type', 'xinetd'],
                                             env=env, timeout=120, check=True, capture_output=True, text=True)
                    for serv in chkconf.stdout.strip().split('\n'):
                        servT = serv.split()
                        try:
                            self._xinetd_services[servT[0].strip(":")] = servT[1] == 'on'
                        except IndexError:
                            continue
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    # TODO return an exception to the exterior
                    print("chkconfig error when trying to list xinetd services", stderr)
        except KeyError:
            return self._xinetd_services

    def _running_systemd(self):
        # TODO : Change to force root command
        try:
            return subprocess.run(['/usr/bin/mountpoint', '-q', '/sys/fs/cgroup/systemd'], env={'PATH': '/usr/bin:/usr/sbin'}, timeout=120).returncode == 0
        except subprocess.TimeoutExpired:
            # TODO : return an exception outside of the function
            print("moutnpoint error when checking systemd: timeout expired.\n")
            return False

    def _has_systemd(self):
        # TODO : Change to force root command
        try:
            return subprocess.run(['/usr/bin/rpm', '-q', 'systemd'], env={'PATH': '/usr/bin:/usr/sbin'}, timeout=120).returncode == 0
        except subprocess.TimeoutExpired:
            # TODO : return an exception outside of the function
            print("rpm error when checking systemd: timeout expired.\n")
            return False

    def set_service(self, service, enable):
        '''
        This function enable/disable at boot the given service
        '''
        # NOTE EnableUnitFiles and DisableUnitFiles don't work with legacy services
        #      and return file not found
        legacy = os.path.isfile("/etc/rc.d/init.d/{}".format(service))
        if service in self._xinetd_services.keys():
            env = {'LANGUAGE': 'C', 'PATH': "/usr/bin:/usr/sbin"}
#            if dbus_context.is_authorized('org.freeedesktop.policykit.exec', {'polkit.icon': 'abcd', 'aaaa': 'zzzz'}, interactive=True):
            #     try:
            #         chkconf = subprocess.run(['/usr/sbin/chkconfig', "-add" if enable else "--del",
            #                                   service], env=env, timeout=120, check=True, capture_output=True, text=True)
            #     except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            #         # TODO return an exception to the exterior
            #         print("chkconfig error when trying to add/delete service", stderr)
            # else:
            #     # TODO return an excpetion to the exterior
            #     print("You are not authorized to perform this action", stderr)

        elif not legacy and (self._running_systemd() or self._has_systemd()):
            service = "{}.service".format(service)
            if enable:
 #               if self.check_permission(self._manager.EnableUnitFiles(), dbus_context):
#                    self._manager.EnableUnitFiles([service.encode()], False, True)
                
