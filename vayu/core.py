import os
import platform
import subprocess
import time
import warnings
from pathlib import Path

import gevent.monkey;
gevent.monkey.patch_all()

import requests

from vayu import utils


class Downloader:
    """
    Write something useful here
    """

    def __init__(self, url, dest=None, auto_start=False, play=False, progress=True):

        self.url = url.strip()
        self.dest = dest
        self.auto_start = auto_start
        self.play = play
        self.progress = progress

        self.session = requests.Session()
        self.session.headers.update(utils.headers)

        # Initialize response
        resp = self.check_connection(self.url)

        # File name extracted from initial HTTP response
        self.filename = Path(utils.get_filename(resp))

        # File size extracted from initial HTTP response
        self.filesize = utils.get_filesize(resp)

        # This stores the extension of file (.mp4, .mp3, etc)
        self.filetype = self.filename.suffix

        # Helps in selecting default download directory
        self.category = utils.get_category(self.filetype)

        # Absolute path of file
        self.save_as = self.resolve_path(self.dest)

        # Stores total number of bytes written to file
        self.downloaded = 0

        self.status = 'initialized'

        self.download_handler()

    def start(self):
        self.status = 'running'
        self.threaded_tasks()
        self.download()
        self.status = 'finished'

    def stop(self, exp_type=None):
        if self.downloaded == self.filesize:
            self.status = 'finished'
            print('Download Complete!')
        elif isinstance(exp_type, (KeyboardInterrupt, SystemExit)):
            self.status = 'killed'
        else:
            self.status = 'stopped'
        self.session.close()

    def resume(self):
        beg = os.path.getsize(self.save_as)
        end = self.filesize
        self.downloaded = beg

        self.threaded_tasks()
        self.status = 'running'
        self.download(beg, end)
        self.status = 'finished'

    def download_handler(self):
        # TODO: Compare files by computing hash.
        # TODO: Cache url and other info for future use.

        loc = Path(self.save_as)
        if loc.exists():
            # If size of both files are same (in bytes)
            # then it's most likely a duplicate file
            if os.path.getsize(loc) == self.filesize:
                warnings.warn('Identical file exists on dir {}'.format(self.save_as))
                choice = utils.user_prompt1()
                # choice 1: download with new filename
                if choice == '1':
                    self.save_as = utils.gen_new_filename(self.save_as)
                    self.start()

                # choice 2: overwrite file
                elif choice == '2':
                    self.start()

                # choice 3: cancel download
                else:
                    self.stop()

            else:
                warnings.warn('Filename collision: {}'.format(self.save_as))
                choice = utils.user_prompt2()

                # choice 1: download with new filename
                if choice == '1':
                    self.save_as = utils.gen_new_filename(self.save_as)
                    print('New save path: {}'.format(self.save_as))
                    self.start()

                # choice 2: resume file download
                elif choice == '2':
                    self.resume()

                # choice 3: cancel download
                else:
                    self.stop()

        elif self.auto_start:
            self.start()

    def download(self, beg=None, end=None):
        header = utils.headers.copy()
        if beg:
            header['Range'] = 'bytes={}-{}'.format(beg, end)
            mode = 'ab'
        else:
            mode = 'wb'

        r = self.session.get(self.url, headers=header, stream=True)
        chunk_size = 1000  # 1000 = 1 kB
        with open(self.save_as, mode=mode) as outfile:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    outfile.write(chunk)
                    self.downloaded += len(chunk)

    def progress_bar(self):
        """
        Updates download progress and transfer rate.
        This piece of code runs after every one second.
        """
        seconds_passed = 0
        next_call = time.perf_counter()
        while True:
            next_call += 1
            temp = self.downloaded
            gevent.sleep(next_call - time.perf_counter())
            seconds_passed += 1
            avg_speed = self.downloaded / seconds_passed
            ins_speed = (self.downloaded - temp) // 1000
            if self.status in {'killed', 'finished', 'stopped'}:
                break
            if self.filesize and avg_speed:
                eta = round(self.filesize / avg_speed, 2)
                progress = round(self.downloaded / self.filesize * 100, 2)
            else:
                eta = progress = '?'

            message = "\rProgress: {} % || Time Left: {} || Speed: {} kB/s" \
                .format(progress, eta, ins_speed)
            print(message, end='')

    def play_media(self, min_bytes=10 ** 7):
        """
        Open a media file with the default application.
        It checks if enough data is available to play the file
        after every five seconds.
        Note: Some video formats cannot be
        """
        min_bytes = max(min_bytes, self.filesize // 100)
        next_call = time.perf_counter()
        while True:
            next_call += 5
            gevent.sleep(next_call - time.perf_counter())
            if self.status in {'killed', 'finished', 'stopped'}:
                break
            if self.downloaded > min_bytes:
                op_sys = platform.system()
                if op_sys == 'Darwin':  # For macOS
                    command = 'open'
                elif op_sys == 'Linux':
                    command = 'xdg-open'
                elif op_sys == 'Windows':
                    return os.startfile(self.save_as)
                else:
                    return None

                return subprocess.call((command, self.save_as),
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.STDOUT)

    def threaded_tasks(self):
        """
        Tasks that need to run concurrently during file download.
        Thread 1: Updates download progress and transfer rate.
        Thread 2: Plays media content in default app.
        """
        if self.progress:
            gevent.spawn(self.progress_bar)

        if self.play:
            if self.category == 'Video':
                gevent.spawn(self.play_media)
            else:
                warnings.warn('File cannot be streamed.')

    def resolve_path(self, dest):
        default_dir = Path('~/Downloads').expanduser()
        if isinstance(dest, str):
            dest = Path(dest)
            if dest.is_dir():
                directory = dest
            else:
                message = "Destination directory doesn't exist. Using default directory."
                warnings.warn(message)
                directory = default_dir / self.category
        else:
            directory = default_dir / self.category

        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory / self.filename

    def check_connection(self, url):
        try:
            resp = self.session.get(url, stream=True)
        except requests.RequestException:
            raise ConnectionError('Error with URL: {}'.format(self.url))
        if not resp.ok:
            raise ConnectionError("Server status is {}.".format(resp.status_code),
                                  "\nCheck: https://httpstatuses.com/")
        return resp

    def __repr__(self):
        info = [
            'URL: {}'.format(self.url),
            'File Name: {}'.format(self.filename),
            'File Size: {}'.format(utils.readable_size(self.filesize)),
            'File Type: {}'.format(self.filetype),
            'Category: {}'.format(self.category),
            'Path: {}'.format(self.save_as),
        ]
        return '\n'.join(info)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(exc_type)
