"""Adds a shell-friendly progress bar to common file operations."""

import shutil
from shutil import copyfileobj
import stat
import os
import zipfile
import tarfile
import enum

from tqdm.auto import tqdm
from tqdm.utils import CallbackIOWrapper
from tqdm import tqdm


__all__ = ["copytree", "move", "extractall", "empty"]


# --------------------------------------------------------------- Copy / Move #

def copytree(origin_path, dest_path, label=None, *args, **kwargs):
    """Adds `tqdm` progress bars to a standard copytree operation.

    Args:
        origin_path (str): Path to a directory you wish to copy recursively.
        dest_path (str): Path you wish to copy the origin to.
        label (str, optional): A label that will be shown in the progress bar.
            If no label is provided, the name of the source directory currently
            being copied will be used.
        args: Optional positional arguments that will be passed to shutil.copy2
        kwargs: Optional keyword arguments that will be passed to shutil.copy2
    """

    # collect all files and directories recursively
    collected_files, collected_dirs = _collect(origin_path)

    items_to_copy = collected_files + collected_dirs

    if label is None:
        label = os.path.basename(origin_path)

    message = "Copying {label}...".format(label=label)

    for item in tqdm(items_to_copy, message):
        dest_item = item.replace(origin_path, dest_path)
        if os.path.isfile(item):
            parent_path = os.path.split(dest_item)[0]
            if not os.path.exists(parent_path):
                os.makedirs(parent_path)
            shutil.copy2(item, dest_item, *args, **kwargs)
        else:
            if not os.path.exists(dest_item):
                os.makedirs(dest_item)


def move(origin_path, dest_path, label=None, *args, **kwargs):
    """Adds `tqdm` progress bars to a standard move operation.

    Args:
        origin_path (str): Path to a directory or file you wish to move.
        dest_path (str): Path you want the file or directory moved to.
        label (str, optional): Label that will be applied to the progress bar.
        args: Optional positional arguments passed to shutil.move
        kwargs: Optional keyword arguments passed to shutil.move
    """
    dest_path = os.path.join(dest_path, os.path.basename(origin_path))
    collected_files, collected_dirs = _collect(origin_path)
    items_to_move = collected_files + collected_dirs
    if label:
        label = "Moving {item}...".format(item=label)
    else:
        label = "Moving..."
    for item in tqdm(items_to_move, "Moving..."):
        dest_item = item.replace(origin_path, dest_path)
        dest_parent_dir = os.path.split(dest_item)[0]
        os.makedirs(dest_parent_dir, exist_ok=True)
        shutil.move(item, dest_item, *args, **kwargs)

        # clean up leftover directories
        if os.path.isfile(origin_path):
            os.remove(origin_path)
        elif os.path.isdir(origin_path):
            shutil.rmtree(origin_path)


# ----------------------------------------------------------------- Utilities #
def _collect(path):
    """Recursively collect sub-directories and files under the given directory.

    Args:
        path (str): Path to a directory

    Returns:
        tuple[list, list]: The lists of files and sub-directories
    """
    collected_files = []
    collected_dirs = []
    for root, dirs, files in os.walk(path, topdown=True):
        collected_files.extend(
            [os.path.join(root, file_) for file_ in files]
        )
        if not files and not dirs:
            collected_dirs.append(root)
    return collected_files, collected_dirs


# ------------------------------------------------------------- File Deletion #

def empty(directory):
    """Adds a `tqdm` progress bar to an "empty" operation.

    Empty means removing all files and sub-directories from a given directory.

    Args:
        directory (str): Path to a directory
    """
    all_files = []
    all_dirs = []
    for root, dirs, files in os.walk(directory):
        all_files.extend(
            [os.path.join(root, file_) for file_ in files]
        )
        all_dirs.extend(
            [os.path.join(root, dir_) for dir_ in dirs]
        )
    all_items = all_files + all_dirs
    for item in tqdm(all_items, "Cleaning up..."):
        try:
            os.remove(item)
        except PermissionError:
            os.chmod(item, stat.S_IWRITE)
            os.remove(item)


# ---------------------------------------------------------- Compressed Files #
# Each type of compressed file does more-or-less the same thing, but they have
# different interfaces.  This module provides interface adapters to make a
# consistent interface when working with compressed files.  We use ZipFile's
# interface for compatibility.

class CompressedFileFormat(enum.Enum):
    """Enumerated compressed file types"""
    ZIP = 0
    TAR = 1
    TARGZ = 2


class _TarFile(tarfile.TarFile):
    """Interface adapter for tar files."""
    def infolist(self):
        """Adapts `TarFile.getmembers` to ZipFile's `infolist`"""
        return [_TarInfo(member) for member in self.getmembers()]

    def extract(self, item, destination):
        """Adapts `TarFile.extractall` to ZipFile's `extract`"""
        super(_TarFile, self).extractall(path=destination, members=item)


class _TarInfo(tarfile.TarInfo):
    """Interface adapter for individual tarred files."""
    @property
    def filename(self):
        """Adapts `TarInfo.name` to ZipFile's `name` attribute."""
        return self.name

    @property
    def file_size(self):
        """Adapts `TarInfo.size` to ZipFile's `file_size` attribute."""
        return self.size


class Extractor(object):
    """Extract tar and zip files with progress bars."""
    type_map = {
        ".tgz": (_TarFile, "r:gz"),
        ".tar.gz": (_TarFile, "r:gz"),
        ".tar": (_TarFile, "r"),
        ".zip": (zipfile.ZipFile, "r"),
    }

    def __init__(self, file_path, label=None):
        """
        Args:
            file_path (str): Path to the compressed file.
            label (str, optional): Label for the `tqdm` progress bar.

        Attributes:
            file_path (str): The full, expanded path to the compressed file
            desc (str): The label that will be applied on the progress bar
            file_type (object): The adapter class that will be used
            open_mode (str): The file read mode appropriate for the given file
            job_size (int): The size of the file being extracted, in bytes

        Raises:
            TypeError: If the given file is not valid for this utility.
        """

        self.file_path = os.path.expandvars(os.path.expanduser(file_path))

        extension = os.path.splitext(self.file_path)[1]

        if label:
            self.desc = "Extracting {item}...".format(item=label)
        else:
            self.desc = "Extracting..."

        try:
            self.file_type, self.open_mode = self.type_map[extension]
        except KeyError:
            raise TypeError(
                ("{file_} does not support extraction through console_utils"
                 "".format(file_=file_path))
            )

        self.job_size = 0

    def extractall(self, extract_to):
        """Extract everything from the given compressed file to the directory.

        This utility adds a shell-friendly progress bar to extraction process

        Args:
            extract_to (str): Path to the directory to extract to
        """
        extract_to = os.path.expandvars(os.path.expanduser(extract_to))

        # make the destination directory if it doesn't already exist
        if not os.path.exists(extract_to):
            os.mkdir(extract_to)
        with self.file_type(self.file_path, self.open_mode) as compressed_file:
            items_to_extract = compressed_file.infolist()
            self.job_size = sum(
                getattr(item, "file_size", 0) for item in items_to_extract
            )
            with self._extract_progress() as progress:
                for item in compressed_file.infolist():
                    self._extract_item(
                        compressed_file, item, extract_to, progress
                    )

    def _extract_item(self, compressed_file, item, extract_to, progress):
        """Extracts a particular item from the compressed file

        Args:
            compressed_file (object): An open file-like object.
            item (object): An info object appropriate to the given file.
            extract_to (str): Path to an extraction directory.
            progress: The active progress bar object.
        """
        try:
            file_size = item.file_size
        except AttributeError:
            file_size = 0

        # item is a directory
        if not file_size:
            compressed_file.extract(item, extract_to)
            return
        with compressed_file.open(item, self.open_mode) as source:
            with open(os.path.join(extract_to, item.filename), "wb") as dest:
                copyfileobj(CallbackIOWrapper(progress.update, source), dest)

    def _extract_progress(self):
        """Wraps an extraction operation in a progress bar."""
        return tqdm(
            desc=self.desc, unit="B", unit_scale=True,
            unit_divisor=1024, total=self.job_size
        )


def extractall(compressed_file, destination, label=None):
    """Extracts the entire contents of a compressed file with a progress bar.

    Args:
        compressed_file (str): Path to a compressed file.
        destination (str): Path to an extraction directory target.
        label (str, optional): Label to be used on the progress bar.
    """
    Extractor(compressed_file, label=None).extractall(destination)
