import requests
import os
import sys
from time import clock

try:
    # python 3
    import urllib.parse as urlparse
except ImportError:
    # python 2
    from urlparse import urlparse


URL = input('Enter URL: ').strip()

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

r = requests.get(URL, headers=header, stream=True)
# print(r.headers)
file_size = r.headers.get('content-length')


def is_downloadable():
    content_type = r.headers.get('Content-Type')
    if 'text' in content_type or 'html' in content_type:
        print("URL done not contain a downloadable resource!")
        c = input('Are you sure you want to continue? (yes/no): ').strip().lower()
        if c not in {'yes', 'y', 'yeah', 'sure', 'yep'}:
            quit()
    return True


def get_file_name():
    if 'Content-Disposition' in r.headers:
        # If the response has Content-Disposition, try to get filename from it
        cd = dict(map(
            lambda x: x.strip().split('=') if '=' in x else (x.strip(), ''),
            r.headers['Content-Disposition'].split(';')))

        if 'filename' in cd:
            filename = cd['filename'].strip("\"'")
            if filename:
                return filename
        if 'filename*' in cd:
            filename = cd['filename*'].strip("UTF-8''")
            return filename

    filename = os.path.basename(urlparse.urlsplit(r.url)[2])
    return urlparse.unquote(filename)


def get_normal_size():
    normal_size = file_size
    suffix = ['Bytes', 'KiloBytes', 'MegaBytes', 'GigaBytes', 'TeraBytes']
    i = 0
    while normal_size >= 1024:
        i += 1
        if i > 4:
            break
        normal_size /= 1024
    return '{} {}'.format(round(normal_size, 4), suffix[i])


def generate_containers():
    d = {
        'zip': 'Compressed', 'rar': 'Compressed', 'r0*': 'Compressed', 'r1*': 'Compressed', 'arj': 'Compressed',
        'gz': 'Compressed', 'sit': 'Compressed', 'sitx': 'Compressed', 'sea': 'Compressed', 'ace': 'Compressed',
        'bz2': 'Compressed', '7z': 'Compressed', 'doc': 'Documents', 'pdf': 'Documents', 'ppt': 'Documents',
        'pps': 'Documents', 'docx': 'Documents', 'pptx': 'Documents', 'mp3': 'Music', 'wav': 'Music', 'wma': 'Music',
        'mpa': 'Music', 'ram': 'Music', 'ra': 'Music', 'aac': 'Music', 'aif': 'Music', 'm4a': 'Music',
        'exe': 'Programs',
        'msi': 'Programs', 'avi': 'Videos', 'mpg': 'Videos', 'mpe': 'Videos', 'mpeg': 'Videos', 'asf': 'Videos',
        'wmv': 'Videos', 'mov': 'Videos', 'qt': 'Videos', 'rm': 'Videos', 'mp4': 'Videos', 'flv': 'Videos',
        'm4v': 'Videos', 'webm': 'Videos', 'ogv': 'Videos', 'ogg': 'Videos', 'mkv': 'Videos'
    }
    return d


def select_path():
    if file_extension in file_containers:
        folder_name = file_containers[file_extension]
    else:
        folder_name = 'Others'
    folder_path = os.path.expanduser('~/Downloads/{}/'.format(folder_name))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    file_path = folder_path + file_name
    return folder_path, file_path


def pre_download_check():
    if os.path.exists(file_path) and os.path.getsize(file_path) == file_size:
        print('Same file already exists. No need to download again!')
    elif os.path.exists(file_path):
        print('File name already exists!')
        c = input('Resume download? (yes/no): ')
        if c in {'yes', 'y', 'yeah', 'sure', 'yep'}:
            download_file(URL, start=os.path.getsize(file_path))
        else:
            print('Aborted...')
            quit()
    else:
        download_file(URL)


def download_file(url, start=0, end=file_size):
    if start != 0 or end != file_size:
        resume_header = header
        resume_header['Range'] = 'bytes={}-{}'.format(start, end + 1)
        r = requests.get(url, headers=resume_header, stream=True, allow_redirects=True)
        print(r.headers)
        print('Resuming download...')
        file_mode = 'ab'
    else:
        r = requests.get(url, headers=header, stream=True)
        file_mode = 'wb'

    is_media = file_containers.get(file_extension) in {'Music', 'Videos'}
    already_played = False
    min_data = 1024 * 1024 * 10
    chunk_size = 1024
    print('chunk size = {}'.format(chunk_size))
    start_time = clock()
    downloaded_data = 0
    with open(file_path, file_mode) as file:
        for chunk in r.iter_content(chunk_size=chunk_size):  # 1024 = 1KB
            if not already_played and is_media and downloaded_data > min_data:
                os.startfile(file_path)
                already_played = True
            if chunk:
                file.write(chunk)
            downloaded_data += len(chunk)
            ads = round(downloaded_data / (1024 * (clock() - start_time)), 2)
            progress = round((start + downloaded_data) / end * 100, 2)
            print('\rAverage speed ==> {} KB/sec\t\t||\t\tProgress ==> {} %'.format(ads, progress), end='')
        # sys.stdout.flush()


if __name__ == '__main__':
    is_downloadable()
    file_name = get_file_name()
    normal_size = get_normal_size()
    file_containers = generate_containers()
    file_extension = file_name[file_name.rfind('.') + 1:]
    folder_path, file_path = select_path()
    print('Size of file: {} {}'.format(normal_size, file_size))
    print('Name of file: {}'.format(file_name))
    # print('File Containers:\n{}'.format(file_containers))
    print('File extension: {}'.format(file_extension))
    pre_download_check()
    r.close()
