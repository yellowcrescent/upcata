#!/usr/bin/python3
# coding: utf-8
# vim: set ts=4 sw=4 expandtab syntax=python:
"""

upcata
Cataclysm DDA experimental build update tool

- Checks and displays info from latest build on GitHub
- Downloads and extracts latest tarball
- Maintains a 'current' symlink that points to latest build
- Makes backups of save and config data during each update

License: MIT

Jacob Hipps <jacob@ycnrg.org>
https://ycnrg.org/

"""

__version__ = '0.1.1'
__date__ = 'Sep 17 2019'

import os
import sys
import re
import shutil
import logging
import tarfile
from argparse import ArgumentParser

import requests
import arrow


logger = logging.getLogger('upcata')
CURRENT_LINK = './current'
USERDATA_DIR = './userdata'


def setup_logging(clevel=logging.INFO, flevel=logging.DEBUG, logfile=None):
    """configure logging using standard logging module"""
    logger.setLevel(logging.DEBUG)

    con = logging.StreamHandler()
    con.setLevel(clevel)
    con_format = logging.Formatter("%(levelname)s: %(message)s")
    con.setFormatter(con_format)
    logger.addHandler(con)

    if logfile:
        try:
            flog = logging.handlers.WatchedFileHandler(logfile)
            flog.setLevel(flevel)
            flog_format = logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s")
            flog.setFormatter(flog_format)
            logger.addHandler(flog)
        except Exception as e:
            logger.warning("Failed to open logfile %s: %s", logfile, str(e))

def get_changes(old, new, prefix='cdda-jenkins-b'):
    """
    Get changes between @old and @new commits/branches
    """
    r = requests.get('https://api.github.com/repos/CleverRaven/Cataclysm-DDA/compare/{}{}...{}{}'.format(prefix, old, prefix, new))
    rjson = r.json()

    try:
        commits = rjson['commits']
    except:
        logger.error("Failed to fetch changes: %s", rjson.get('message'))
        return []

    chglog = [ "{ts} [{commit[author][name]}] {msg}".format(
                msg=x['commit']['message'].replace('\n\n', '\n').replace('\n', '\n\t').strip(),
                ts=arrow.get(x['commit']['author']['date']).format("MMM DD YYYY"),
                **x) for x in sorted(commits, key=lambda x: x['commit']['author']['date'], reverse=True) ]

    return chglog

def get_latest_release(platform, prefix='cdda-jenkins-b'):
    """
    Get latest Cata release for @platform
    """
    r = requests.get('https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases')
    releases = r.json()

    tlatest = None
    for trel in releases:
        if len([ x for x in trel['assets'] if x['label'].lower() == platform.lower() ]):
            tlatest = trel
            break

    if tlatest is None:
        logger.error("No build for %s available!", platform)
        return None

    tlatest['build'] = tlatest['tag_name'].replace(prefix, '')
    tlatest['tasset'] = [ x for x in tlatest['assets'] if x['label'].lower() == platform.lower() ][0]
    return tlatest

def get_current_release(cpath=CURRENT_LINK):
    """
    Determine current release version
    """
    try:
        tlink = os.readlink(cpath)
    except Exception as e:
        logger.warning("Unable to determine current release: %s", str(e))
        return None

    try:
        res = re.match(r'^cataclysmdda-(?P<version>[0-9A-Z\.]+)-b?(?P<build>[0-9]+)$', tlink, re.I).groupdict()
    except Exception:
        logger.warning("Unable to parse release/version info from symlink '%s'", cpath)
        return None

    resdate = arrow.get(os.stat('./current').st_mtime).format("MMM DD, YYYY HH:MM")
    logger.info("Local build: %s (updated %s)", res['build'], resdate)

    return res['build']

def download_release(url, filename, save_prefix='./'):
    """
    Download release from @url and save to @save_prefix
    """
    lpath = os.path.realpath(os.path.join(save_prefix, filename))

    logger.info("Fetching update: %s --> %s", url, lpath)
    sys.stdout.write("*** Downloading...")

    with open(lpath, 'wb') as f:
        with requests.get(url, allow_redirects=True, stream=True) as r:
            try:
                r.raise_for_status()
            except Exception as e:
                sys.stdout.write("\n")
                logger.error("Error while fetching update from <%s>: %s", url, str(e))
                return None

            itx = 0
            for tchunk in r.iter_content(chunk_size=32768):
                if tchunk:
                    f.write(tchunk)
                    if not itx % 32:
                        sys.stdout.write('.')
                        sys.stdout.flush()
    sys.stdout.write("\n")
    logger.info("Download complete")
    return lpath

def extract_tarball(tarball, prefix='./'):
    """
    Extract tarball to @prefix
    """
    ppath = os.path.realpath(prefix)
    logger.info("Extracting archive to prefix [%s] ...", ppath)

    try:
        with tarfile.open(tarball, 'r') as f:
            # Get top-level directory name
            topdir = f.getmembers()[0].name.split('/')[0]
            rtopdir = os.path.realpath(os.path.join(ppath, topdir))

            # Ensure topdir does not already exist
            if os.path.exists(rtopdir):
                logger.error("Path [%s] already exists! Move or delete directory first.", rtopdir)
                return None

            # Extract all the things
            f.extractall(path=ppath)

    except Exception as e:
        logger.error("Failed to extract archive: %s", str(e))
        return None

    logger.info("Extracted archive successfully")
    return topdir

def backup_data():
    """
    Backup userdata (saves, config, etc.)
    """
    srcdir = os.path.realpath(USERDATA_DIR)
    savedir = os.path.realpath("save-" + arrow.get().format('YYYYMMDD-HHMMSS'))

    logger.info("Backing up user save and config data to [%s] ..." % (savedir))
    try:
        shutil.copytree(srcdir, savedir, symlinks=True)
    except Exception as e:
        logger.error("Failed to copy save data: %s", str(e))
        return None

    logger.info("Backup complete")
    return savedir

def parse_cli():
    """parse CLI options with argparse"""
    aparser = ArgumentParser(description="Cataclysm DDA updater")
    aparser.set_defaults(release=None, update=False, logfile=None, loglevel=logging.INFO)

    aparser.add_argument("release", action="store", nargs="?", metavar="RELEASE", help="Release number")
    aparser.add_argument("--update", "-u", action="store_true", help="Update to latest (or specified) release")
    aparser.add_argument("--debug", "-d", action="store_const", dest="loglevel", const=logging.DEBUG, help="Show debug messages")
    aparser.add_argument("--logfile", "-l", action="store", metavar="LOGPATH",
                         help="Path to output logfile [default: %(default)s]")
    aparser.add_argument("--version", "-V", action="version", version="%s (%s)" % (__version__, __date__))
    return aparser.parse_args()

def _main():
    """
    Entry point
    """
    args = parse_cli()
    setup_logging(args.loglevel, logfile=args.logfile)

    rlocal = get_current_release()
    rlatest = get_latest_release('Linux_x64 Tiles')

    if not rlatest:
        sys.exit(1)

    if rlocal == rlatest['build']:
        logger.info("Up-to-date on build %s", rlatest['build'])
        return

    # Show build info
    print("*** New build available! ***")
    print("Build %s (%s)" % (rlatest['build'], arrow.get(rlatest['published_at']).format("MMM DD, YYYY HH:MM (Z)")))
    print("%s %s" % (rlatest['name'], '[EXPERIMENTAL]' if rlatest.get('prerelease') else '[STABLE]'))
    print("Commit: %s @ %s" % (rlatest['target_commitish'], rlatest['tag_name']))
    print("****************************")

    # Show changes
    if rlocal:
        print("Changes since your local build (#%s):\n" % (rlocal))
        for tline in get_changes(rlocal, rlatest['build']):
            print("  %s" % (tline))
        print("****************************")

    # Update mode
    if args.update:
        logger.info("Updating to latest release.")

        # Fetch latest release tarball
        tball = download_release(rlatest['tasset']['browser_download_url'], rlatest['tasset']['name'])
        if not tball:
            logger.critical("Download failed. Aborting.")
            sys.exit(2)

        # Extract tarball
        tdir = extract_tarball(tball)
        if not tdir:
            logger.critical("Extraction failed. Aborting.")
            sys.exit(2)

        # Add version/build suffix to directory
        newpath = tdir + '-' + rlatest['build']
        try:
            os.rename(tdir, newpath)
        except Exception as e:
            logger.error("Failed to rename directory: %s", str(e))
            sys.exit(2)

        # Recreate symlink to point to new version
        linkpath = os.path.abspath(CURRENT_LINK)
        try:
            os.unlink(linkpath)
        except:
            logger.warning("Failed to remove symlink: %s", linkpath)
        os.symlink(newpath, linkpath)

        # Ensure userdata directory exists
        ud_save = os.path.realpath(os.path.join(USERDATA_DIR, 'save'))
        ud_config = os.path.realpath(os.path.join(USERDATA_DIR, 'config'))
        ud_sound = os.path.realpath(os.path.join(USERDATA_DIR, 'sound'))
        if not (os.path.exists(ud_save) and \
                os.path.exists(ud_config) and \
                os.path.exists(ud_sound)):
            logger.info("Creating missing userdata directories")
            try:
                os.makedirs(os.path.join(USERDATA_DIR, 'save'))
                os.makedirs(os.path.join(USERDATA_DIR, 'config'))
                os.makedirs(os.path.join(USERDATA_DIR, 'sound'))
            except Exception as e:
                logger.error("Failed to create missing userdata directories: %s", str(e))

        # Create data symlinks in new directory
        os.symlink(os.path.realpath(os.path.join(USERDATA_DIR, 'save')), os.path.join(newpath, 'save'))
        os.symlink(os.path.realpath(os.path.join(USERDATA_DIR, 'config')), os.path.join(newpath, 'config'))
        os.symlink(os.path.realpath(os.path.join(USERDATA_DIR, 'sound')), os.path.join(newpath, 'sound'))

        # Backup data
        savedir = backup_data()
        if savedir is None:
            logger.warning("Backup for save & config data failed!")
            curbackup = None
        else:
            curbackup = os.path.basename(savedir)

        logger.info("Upgrade complete")
        print("\n****************************")
        print("*** Current build: %s" % (get_current_release()))
        print("*** Latest backup: %s" % (curbackup))
        print("Finished.")
    else:
        print("\n>> Use -u option to update to the latest release.\n")

if __name__ == '__main__':
    _main()
