import datetime
import platform
import subprocess
import sys
import time
import threading
import warnings
from pathlib import Path
import requests

from vayu import utils


class Downloader:
    """
    Write something useful here
    """

    def __init__(self, url, dest=None, auto_start=True, play=False, progress=True):
        self.url = url
        self.dest = dest
        self.auto_start = auto_start
        self.play = play
        self.progress = progress

        self.session = requests.Session()
        self.session.headers.update(utils.headers)

        resp = self.check_connection(self.url)
        self.filename = utils.get_filename(resp)
        self.filesize = utils.get_filesize(resp)
        self.category = utils.get_category(self.filename)
        self.save_as = self.get_save_path(self.dest)

        self.downloaded = 0
        self.status = None
        print(self.__repr__())

        self.start()

    def start(self):
        self.threaded_tasks()
        self.status = 'running'
        self.download()
        self.status = 'finished'

    def stop(self, exp_type):
        if self.downloaded == self.filesize:
            self.status = 'finished'
        if isinstance(exp_type, (KeyboardInterrupt, SystemExit)):
            self.status = 'killed'
        self.session.close()

    def resume(self):
        pass

    def download_handler(self):
        # TODO complete this function
        def prompt1():
            warnings.warn('Same file already exists!')
            print('  Select an option:')
            options = ['overwrite: 1', 'rename: 2', 'cancel: 3']

        def prompt2():
            warnings.warn('File name collision!')
            print('  Select an option:')
            options = ['resume: 1', 'rename: 2', 'cancel: 3']

        loc = Path(self.save_as)
        if loc.exists():
            if loc.stat().st_size == self.filesize:
                pass
            else:
                pass
        else:
            if self.auto_start:
                self.start()

    def download(self, beg=None, end=None):
        header = utils.headers.copy()
        if beg:
            header['Range'] = f'bytes={beg}-{end}'
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

    def _progress(self):
        """
        Updates download progress after every one second.
        """
        next_call = time.perf_counter()
        while True:
            next_call += 1
            current = self.downloaded
            time.sleep(next_call - time.perf_counter())
            if self.status in {'killed', 'finished'}:
                break
            if self.filesize:
                progress = round(self.downloaded / self.filesize * 100, 2)
            else:
                progress = '?'
            d = datetime.datetime.now().strftime('%S.%f')[:-4]
            message = f'\rProgress --> {progress} % | {d} | ' \
                f'Speed --> {(self.downloaded - current) // 1000} kB/s '
            print(message, end='')

        if self.status == 'finished':
            print('\rDownload Complete!')

    def play_media(self, min_bytes=10**7):
        """
        Open a media file with the default application.
        It checks if enough data is available to play the file
        after every five seconds.
        """
        next_call = time.perf_counter()
        while True:
            next_call += 5
            time.sleep(next_call - time.perf_counter())
            if self.downloaded > min_bytes:
                op_sys = platform.system()
                if op_sys == 'Darwin':  # For macOS
                    command = 'open'
                elif op_sys == 'Windows':
                    command = 'start'
                elif op_sys == 'Linux':
                    command = 'xdg-open'
                else:
                    return None

                return subprocess.call((command, self.save_as),
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.STDOUT)

    def threaded_tasks(self):
        """
        Tasks that need to run concurrently during file download
        """
        if self.progress:
            t1 = threading.Thread(target=self._progress)
            t1.daemon = True
            t1.start()
            
        if self.play and self.category == 'Video':
            t2 = threading.Thread(target=self.play_media)
            t2.daemon = True
            t2.start()

    def check_connection(self, url):
        try:
            resp = self.session.get(url, stream=True, allow_redirects=True)
        except requests.RequestException as exp:
            print(exp)
            sys.exit()
        return resp

    def get_save_path(self, dest):
        if dest and Path(dest).is_dir():
            self.dest = Path(dest)
        else:
            self.dest = Path.expanduser(Path('~/Downloads')) / self.category

        Path(self.dest).mkdir(parents=True, exist_ok=True)
        file_path = self.dest / self.filename
        return file_path

    def __repr__(self):
        info = [
            f'URL: {self.url}',
            f'File Size: {utils.readable_size(self.filesize)}',
            f'File Name: {self.filename}',
            f'Category: {self.category}',
            f'Path: {self.save_as}',
        ]
        return '\n'.join(info)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(exc_type)


#
# # from vayu import Downloader as dl
#
# url = input('Enter URL: ').strip()
# Downloader(url)
print('hey')
