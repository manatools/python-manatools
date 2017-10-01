# python-manatools #

![logo](https://avatars3.githubusercontent.com/u/19332721?v=3&s=200 "Python ManaTools")

Python ManaTools starts from the experience of tools and framework 
written in Perl, since most systemd and dbus API are python based 
instead a this way seemed to be natural.

Python ManaTools aim is to help in writing tools based on libYui 
(Suse widget abstraction library), to be collected under the same
ManaTool hat and hopefully with the same look and feel.

Every output modules can of course be run using QT, Gtk or ncurses 
interface.

## REQUIREMENTS

### SUSE libyui
* https://github.com/libyui/libyui

### libyui-mga - our widget extension
* https://github.com/manatools/libyui-mga

### SUSE libyui-bindings - anaselli fork
* For references, master is https://github.com/libyui/libyui-bindings
* To use libyui-mga extension we added some patches to original sources get them from mageia package at http://svnweb.mageia.org/packages/cauldron/libyui-bindings/current/SOURCES/

### at least one of the SUSE libyui plugins
* libyui-gtk     - https://github.com/libyui/libyui-gtk
* libyui-ncurses - https://github.com/libyui/libyui-ncurses
* libyui-qt      - https://github.com/libyui/libyui-qt
* Consider here also to check some patches we could add to original sources looking at mageia packages http://svnweb.mageia.org/packages/cauldron/libyuiXXXX/current/SOURCES/ (where XXXX is nothing for libyui and -gtk, -qt, -ncurses for plugins)

## INSTALLATION
python setup.py install
