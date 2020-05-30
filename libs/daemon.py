#!/usr/bin/env python
#
# $Id: daemon.py 7274 2008-03-05 01:00:09Z bmc $

# NOTE: Documentation is intended to be processed by epydoc and contains
# epydoc markup.

"""
Overview
========

Convert the calling process to a daemon. To make the current Python process
into a daemon process, you need two lines of code::

    import daemon
    daemon.daemonize()

If C{daemonize()} fails for any reason, it throws an exception. It also
logs debug messages, using the standard Python 'logging' package, to
channel 'daemon'.

Adapted from:

  - U{http://www.clapper.org/software/daemonize/}

See Also
========

Stevens, W. Richard. I{Unix Network Programming} (Addison-Wesley, 1990).
"""

__version__ = "1.0.1"
__author__ = "Brian Clapper, bmc@clapper.org"
__url__ = "http://www.clapper.org/software/python/daemon/"
__copyright__ = "(c) 2008 Brian M. Clapper"
__license__ = "BSD-style license"

__all__ = ["daemonize", "DaemonError"]

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import logging
import os
import sys
import signal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default daemon parameters.
# File mode creation mask of the daemon.
UMASK = 0o077

# Default working directory for the daemon.
WORKDIR = "/"

# Default maximum for the number of available file descriptors.
MAXFD = 1024

# The standard I/O file descriptors are redirected to /dev/null by default.
if hasattr(os, "devnull"):
    NULL_DEVICE = os.devnull
else:
    NULL_DEVICE = "/dev/null"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("daemonize")

# ---------------------------------------------------------------------------
# Public classes
# ---------------------------------------------------------------------------


class DaemonError(Exception):
    """
    Thrown by C{daemonize()} when an error occurs while attempting to create
    a daemon. A C{DaemonException} object always contains a single string
    value that contains an error message describing the problem.
    """

    def __init__(self, error_message):
        """
        Create a new C{DaemonException}.

        @type error_message:  string
        @param error_message: the error message
        """
        self.error_message = error_message

    def __str__(self):
        """
        Get a string version of the exception.

        @return: a string representing the exception
        """
        return self.error_message


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def daemonize(no_close=False):
    """
    Convert the calling process into a daemon.

    @type no_close:  boolean
    @param no_close: If True, don't close the file descriptors. Useful
                     if the calling process has already redirected file
                     descriptors to an output file. WARNING: Only set this
                     parameter to True if you're SURE there are no open file
                     descriptors to the calling terminal. Otherwise, you'll
                     risk having the daemon re-acquire a control terminal,
                     which can cause it to be killed if someone logs off that
                     terminal.

    @raise DaemonException: Error during daemonizing
    """
    global log

    if os.name != "posix":
        log.warning("Daemon is only supported on Posix-compliant systems.")
        return

    try:
        # Fork once to go into the background.

        pid = _fork()
        if pid != 0:
            # Parent. Exit using os._exit(), which doesn't fire any atexit
            # functions.
            os._exit(0)

        # First child. Create a new session. os.setsid() creates the session
        # and makes this (child) process the process group leader. The process
        # is guaranteed not to have a control terminal.
        os.setsid()

        # Ignore SIGHUP
        signal.signal(signal.SIGHUP, signal.SIG_IGN)

        # Fork a second child to ensure that the daemon never reacquires
        # a control terminal.
        pid = _fork()
        if pid != 0:
            # Original child. Exit.
            os._exit(0)

        # This is the second child. Set the umask.
        os.umask(UMASK)

        # Go to a neutral corner (i.e., the primary file system, so
        # the daemon doesn't prevent some other file system from being
        # unmounted).
        os.chdir(WORKDIR)

        # Unless `no_close` was specified, close all file descriptors.
        if not no_close:
            _redirectFileDescriptors()

    except Exception as e:
        raise DaemonError("Error during daemonizing: {0}".format(repr(e)))


# ---------------------------------------------------------------------------
# Private functions
# ---------------------------------------------------------------------------


def _fork():
    try:
        return os.fork()
    except OSError as e:
        raise DaemonError("Cannot fork: %s [%d]" % (e.strerror, e.errno))


def _redirectFileDescriptors():
    import resource  # POSIX resource information

    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = MAXFD

    # Close all file descriptors.

    for fd in range(0, maxfd):
        # Only close TTYs.
        try:
            os.ttyname(fd)
        except:
            continue

        try:
            os.close(fd)
        except OSError as e:
            # File descriptor wasn't open. Ignore.
            logging.info("Error in _redirectFileDescriptors 1: {0}".format(repr(e)))
        except Exception as e:
            logging.info("Error in _redirectFileDescriptors 2: {0}".format(repr(e)))

    # Redirect standard input, output and error to something safe.
    # os.open() is guaranteed to return the lowest available file
    # descriptor (0, or standard input). Then, we can dup that descriptor
    # for standard output and standard error.

    os.open(NULL_DEVICE, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)


# ---------------------------------------------------------------------------
# Main program (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    log = logging.getLogger("daemon")
    hdlr = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%T")
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    log.setLevel(logging.DEBUG)

    log.debug("Before daemonizing, PID=%d" % os.getpid())
    daemonize(no_close=True)
    log.debug("After daemonizing, PID=%d" % os.getpid())
    log.debug("Daemon is sleeping for 10 seconds")

    import time

    time.sleep(10)

    log.debug("Daemon exiting")
    sys.exit(0)
