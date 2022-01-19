import gettext, locale
import sys, os
from optparse import OptionParser, SUPPRESS_HELP

from .log import start as logstart
from .constants import LOCALE_DIR, APP, VERSION, REVISION, PLUGIN_DIR
from .helper import debug, info, error

if REVISION:
    VERSION = '%s (git: %s)' % (VERSION, REVISION)

__listener = None

def get_listener():
    global __listener
    if __listener is None:
        from .listener import Listener
        __listener = Listener()
    
    return __listener

def get_parser (use_ = False):

    if not use_: _ = lambda s : s
    
    desc = "%prog - A Portage GUI."
    usage = "%prog [options]"
    vers =  "%%prog v. %s" % VERSION

    parser = OptionParser(version = vers, prog = "portato", description = desc, usage = usage)
    
    parser.add_option("--mq", action = "store", nargs = 1, type="long", dest = "mq", default = None,
            help = SUPPRESS_HELP)

    parser.add_option("-F", "--no-fork", action = "store_true", dest = "nofork", default = False,
            help = _("do not fork off as root"))

    parser.add_option("--plugin-dir", action = "store_true", dest = "pdir", default = False,
            help = _("print the directory the plugins are located in"))

    return parser

def _sub_start ():
    locale.setlocale(locale.LC_ALL, '')
    gettext.install(APP, LOCALE_DIR, unicode = True)

def start():

    _sub_start()

    logstart(file=False)

    (options, args) = get_parser().parse_args()

    if options.pdir:
        print PLUGIN_DIR
        return

    if options.nofork or os.getuid() == 0: 
        import atexit
        atexit.register(get_listener().close)

        logstart(file = True) 
        from .gui import run
        info("%s v. %s", _("Starting Portato"), VERSION)
        
        get_listener().set_send(options.mq)
        
        try:
            run()
        except KeyboardInterrupt:
            debug("Got KeyboardInterrupt.")
        
    else: 
        from . import ipc
        import subprocess, threading
        from .su import detect_su_command

        mq = ipc.MessageQueue(None, create = True, exclusive = True)
        
        lt = threading.Thread(target=get_listener().set_recv, args = (mq,))
        lt.setDaemon(False)
        lt.start()
        
        try:
            env = os.environ.copy()
            env.update(DBUS_SESSION_BUS_ADDRESS="")
            
            su = detect_su_command()
            if su:
                debug("Using '%s' as su command.", su.bin)
                cmd = su.cmd("%s --no-fork --mq %ld" % (sys.argv[0], mq.key))

                sp = subprocess.Popen(cmd, env = env)

                try:
                    sp.wait()
                    debug("Subprocess finished")
                except KeyboardInterrupt:
                    debug("Got KeyboardInterrupt.")

            else:
                error(_("No valid su command detected. Aborting."))
        
        finally:
            if lt.isAlive():
                debug("Listener is still running. Close it.")
                get_listener().close()
                lt.join()

            try:
                mq.remove()
            except ipc.MessageQueueRemovedError:
                debug("MessageQueue already removed. Ignore.")
