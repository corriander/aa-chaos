#!/usr/bin/python3
import os
import argparse
from datetime import datetime

from aachaos import get, store

T_ELAPSED_MIN = 10800 # s, minimum elapsed time.

def main(user, passwd):
    """Download quota and store locally.

    Takes a single argument which may be a file path or a 2-tuple
    containing username and password strings; only downloads quota if
    sufficient time has passed since the last fetch (currently 3
    hours).
    """

    # Pre-requisites
    ## Database check (TODO: store this in a static file in XDG_DATA)
    db = store.DB()
    cursor = db.execute("SELECT max(timestamp) FROM quota_history")
    max_tstamp = cursor.fetchone()[0]
    try:
        t_latest = db.dbdt_to_pydt(max_tstamp)
        t_elapsed = datetime.now() - t_latest
        if t_elapsed.total_seconds() < T_ELAPSED_MIN:
            return
    except TypeError as err:
        if 'Must be str, not None' in str(err):
            pass

    info = get.LineInfo(user, passwd)
    db.insert_quota(*info.quota)
    db.commit()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Fetch internet usage/quota."
    )
    parser.add_argument('--user', dest='user')
    parser.add_argument('--pass', dest='passwd')
    #parser.add_argument('--file', dest='fpath')
    args = parser.parse_args()

    #fpath = args.fpath
    #user_passwd = (args.user, args.passwd)
    auth = get.Credentials(args.user, args.passwd)
    #if fpath is not None:
    #    try:
    #        #if (oct(os.stat(fpath).st_mode & 0o777) != '600'):
    #        #    raise Exception("Credential file needs 600 perms")
    #        #else:
    #        with open(fpath, 'r') as f:
    #            auth = tuple(f.readline().strip().split(':'))
    #    except:
    #        raise

    #elif all(arg is not None for arg in user_passwd):
    #    auth = user_passwd
    #else:
    #    raise Exception

    #main(*auth)
    main(auth.user, auth.passwd)
