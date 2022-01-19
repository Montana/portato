import os
from subprocess import Popen

try:
    import pynotify
except ImportError:
    pynotify = None

from .constants import APP
from .helper import debug, warning, error
from . import ipc


class Listener(object):
    def set_recv(self, mq):

        self.mq = mq

        while True:
            try:
                msg, type = self.mq.receive()

                data = msg.split("\0")
                debug("Listener received: %s", data)

                if data[0] == "notify":
                    self.do_notify(*data[1:])
                elif data[0] == "cmd":
                    self.do_cmd(data[1:])
                elif data[0] == "close":
                    break
            except KeyboardInterrupt:
                debug("Got KeyboardInterrupt. Aborting.")
                break
            except ipc.MessageQueueRemovedError:
                debug("MessageQueue removed. Aborting.")
                break

        self.mq = None

    def do_cmd(self, cmdlist):
        """Starts a command as the user.

        @param cmdlist: list of command (options)
        @type cmdlist: string[]"""

        Popen(cmdlist)

    def do_notify(self, base, descr, icon, urgency=None):
      
        if pynotify and os.getuid() != 0:
            if not pynotify.is_initted():
                pynotify.init(APP)

            n = pynotify.Notification(base, descr, icon)
            if urgency is not None and urgency != "":
                n.set_urgency(int(urgency))
            n.show()

    def set_send(self, mq=None):
        if mq is None:
            warning(_("Listener has not been started."))
            self.mq = None
        else:
            self.mq = ipc.MessageQueue(mq)

    def __send(self, string):
        try:
            self.mq.send(string)
        except ipc.MessageQueueError as e:
            error(
                _("An exception occured while accessing the message queue: %s"
                  ), e)

    def send_notify(self, base="", descr="", icon="", urgency=None):
        if self.mq is None:
            self.do_notify(base, descr, icon, urgency)
        else:
            string = "\0".join(["notify", base, descr, icon])

            if urgency is not None:
                string += "\0%d" % urgency
            else:
                string += "\0"

            self.__send(string)

    def send_cmd(self, cmdlist):
        if self.mq is None:
            self.do_cmd(cmdlist)
        else:
            self.__send("\0".join(["cmd"] + cmdlist))

    def close(self):
        if self.mq is not None:
            self.__send("close")
