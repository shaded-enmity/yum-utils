# Copyright (C) 2015  Red Hat, Inc.
#
# Authors: Pavel Odvody <podvody@redhat.com>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
from yum.plugins import TYPE_CORE
from os import walk, path, fstat

requires_api_version = '2.3'
plugin_type = (TYPE_CORE,)

def _stat_ino_fp(fp):
        """
        Get the inode number from file descriptor
        """
        return fstat(fp.fileno()).st_ino

def get_file_list(rpmpath):
        """
        Enumerate all files in a directory
        """
        for root, _, files in walk(rpmpath):
                for f in files:
                        yield path.join(root, f)

def for_each_file(files, cb, m='rb'):
        """
        Open each file with mode specified in `m`
        and invoke `cb` on each of the file objects
        """
        if not files or not cb:
                return []
        ret = []
        for f in files:
                with open(f, m) as fp:
                        ret.append(cb(fp))
        return ret

def do_detect_copy_up(files):
        """
        Open the files first R/O, then R/W and count unique
        inode numbers
        """
        num_files = len(files)
        lower = for_each_file(files, _stat_ino_fp, 'rb')
        upper = for_each_file(files, _stat_ino_fp, 'ab')
        diff = set(lower + upper)
        return len(diff) - num_files

def raw_copy_up(files):
        """
        Induce a copy-up by opening R/W
        """
        return for_each_file(files, _stat_ino_fp, 'ab')

def should_be_verbose(cmd):
        """
        If the debuglevel is > 2 then be verbose
        """
        if not hasattr(cmd, 'debuglevel'):
                return False
        return cmd.debuglevel > 2

def prereposetup_hook(conduit):
        rpmdb_path = conduit.getRpmDB()._rpmdbpath

        try:
                files = list(get_file_list(rpmdb_path))
                if should_be_verbose(conduit.getCmdLine()[0]):
                        conduit.info(1, "ovl: Copying up (%i) files from OverlayFS lower layer" % do_detect_copy_up(files))
                else:
                        raw_copy_up(files)
        except Exception as e:
                conduit.error(1, "ovl: Error while doing RPMdb copy-up:\n%s" % e)
