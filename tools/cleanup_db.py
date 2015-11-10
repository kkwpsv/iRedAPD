#!/usr/bin/env python

# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Cleanup expired throttle and greylisting tracking records.

import os
import sys
import time
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools import debug, logger, get_db_conn, sql_count_id

web.config.debug = debug

backend = settings.backend
logger.info('* Backend: %s' % backend)

now = int(time.time())

conn_iredapd = get_db_conn('iredapd')

#
# Throttling
#
logger.info('* Remove expired throttle tracking records.')

# count existing records
total_before = sql_count_id(conn_iredapd, 'throttle_tracking')

# Delete
conn_iredapd.delete('throttle_tracking',
                    where='init_time + period < %d' % now)

# count left records
total_after = sql_count_id(conn_iredapd, 'throttle_tracking')

logger.info('  - %d removed, %d left.' % (total_before - total_after, total_after))


#
# Greylisting tracking records.
#
logger.info('* Remove expired greylisting tracking records.')

# count existing records
total_before = sql_count_id(conn_iredapd, 'greylisting_tracking')

# Delete
conn_iredapd.delete('greylisting_tracking', where='record_expired < %d' % now)

# count left records
total_after = sql_count_id(conn_iredapd, 'greylisting_tracking')

logger.info('  - %d removed, %d left.' % (total_before - total_after, total_after))

# TODO Count passed sender domain and whitelist its IP address with comment (domain name).
