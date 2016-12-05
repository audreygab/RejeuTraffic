# -*- coding: utf-8 -*-

from ivy.std_api import *
from optparse import OptionParser
import logging
import signal
from pyrejeu.clock import RejeuClock
from pyrejeu.importations import RejeuImportation
from pyrejeu import utils as ut

logger = logging.getLogger('Ivy')

logging.basicConfig(format='%(asctime)-15s - %(levelname)s - %(message)s', level=logging.DEBUG)

def on_cx_proc(agent, connected):
    if connected == IvyApplicationDisconnected:
        logger.error('Ivy application %r was disconnected', agent)
    else:
        logger.info('Ivy application %r was connected', agent)

def on_die_proc(agent, _id):
    logger.info('received the order to die from %r with id = %d', agent, _id)

def connect(app_name, ivy_bus):
    IvyInit(app_name,                   # Nom de l'application fournie à Ivy
            "[%s ready]" % app_name,    # Message 'ready'
            0,                          # main loop is local (ie. using IvyMainloop)
            on_cx_proc,                 # handler appelé sur connexion/déconnexion
            on_die_proc)
    IvyStart(ivy_bus)

if __name__ == "__main__":
    # importation du fichier
    import_obj = RejeuImportation()
    import_obj.import_file(sys.argv[1])

    # gestion des options
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.set_defaults(ivy_bus="127.255.255.255:2010", verbose=False, app_name="RejeuTrafic")
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                      help='Be verbose.')
    parser.add_option('-b', '--ivybus', type='string', dest='ivy_bus',
                      help='Bus id (format @IP:port, default to 127.255.255.255:2010)')
    parser.add_option('-a', '--appname', type='string', dest='app_name',
                      help='Application Name')
    (options, args) = parser.parse_args()

    # initialisation du log
    level = logging.INFO
    if options.verbose:  # Si mode verbeux choisi
        level = logging.DEBUG
    logger.setLevel(level)

    # connection au bus ivy
    logger.info("Connexion to Ivy bus")
    connect(options.app_name, options.ivy_bus)

    clock = RejeuClock(ut.str_to_sec("11:58:55"))

    # gestion des signaux
    def handler(signum, frame):
        clock.stop()
        IvyStop()
        logging.info("Clock stopped")

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    #Lancement de l'horloge
    clock.run()

