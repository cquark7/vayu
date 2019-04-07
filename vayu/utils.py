import cgi
import re
from pathlib import Path
from urllib import parse

import lxml.html

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
}

containers = {
    'Compressed': {'r0*', 'ace', 'bz2', '7z', 'r1*', 'arj', 'rar', 'zip', 'sit', 'gz', 'sea', 'sitx'},
    'Documents': {'pps', 'doc', 'pdf', 'ppt', 'docx', 'pptx'},
    'Music': {'mpa', 'aac', 'ra', 'aif', 'mp3', 'm4a', 'wma', 'ram', 'wav'},
    'Programs': {'msi', 'exe'},
    'Video': {'flv', 'mp4', 'mpe', 'mkv', 'm4v', 'ogv', 'wmv', 'mov', 'rm', 'asf', 'webm', 'avi', 'qt', 'mpg',
              'mpeg', 'ogg'}
}


def _get_valid_filename(s):
    """
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; and remove anything
    that is not an alphanumeric, dash, underscore, space or dot.
    :param s: str
    """
    s = str(s).strip()
    s = re.sub(r'(?u)[^-\w. ]', '', s)
    return ' '.join(s.split())


def get_filename(resp):
    """
    Returns a valid file name by extracting it from the HTTP response
    if response headers contain `Content-Disposition`.
    Otherwise, it parses filename from the URL.
    :param resp: requests.Response
    :return: str
    """
    cd = resp.headers.get('Content-Disposition', None)
    if cd:
        value, params = cgi.parse_header(cd)
        if 'filename' in params:
            return params.get('filename')
        elif 'filename*' in params:
            return params.get('filename*')

    fn = Path(parse.urlsplit(resp.url)[2]).name
    fn = parse.unquote(fn)
    content_type = resp.headers.get('Content-Type')
    idx = fn.rfind('.')
    if not fn or ('html' in content_type and idx == -1):
        title = lxml.html.fromstring(resp.content).find(".//title")
        fn = title.text + '.htm'

    return _get_valid_filename(fn)


def get_filesize(resp):
    """
    Returns file size in bytes
    :param resp: requests.Response
    :return: int or NoneType
    """
    fs = resp.headers.get('content-length', None)
    return int(fs) if fs else fs


def get_category(filetype):
    """
    Returns the category of file using its file extension
    Categories: Video, Music, Compressed, etc
    """
    ext = filetype.lstrip('.')
    for category in containers:
        if ext in containers[category]:
            return category
    return 'Others'


def is_downloadable(resp):
    content_type = resp.headers.get('Content-Type')
    # URL done not contain a downloadable resource!
    if 'text' in content_type or 'html' in content_type:
        return False
    return True


def is_resumable(resp):
    if resp.status_code == 206:
        return True
    return False


def readable_size(size):
    """
    Returns file size in human readable format.
    In this specific function 1 KB = 1024 bytes.
    :param size: size in Bytes
    :return: str
    """
    if size is None:
        return None
    suffix = ['Bytes', 'KiloBytes', 'MegaBytes', 'GigaBytes', 'TeraBytes']
    i = 0
    while size >= 1024:
        i += 1
        size /= 1024
    return f'{round(size, 2)} {suffix[i]}'


def gen_new_filename(loc):
    """
    Generates new filename when there is filename collision.
    :param loc: absolute path of file
    :return: pathlib.Path object
    """
    loc = Path(loc)
    directory = loc.parent
    fn = loc.stem
    ext = loc.suffix
    x = 1
    while True:
        if loc.exists() is False:
            break
        new_fn = f'{fn}_{x}'
        loc = directory / (new_fn + ext)
        x += 1
    return loc


def user_prompt1():
    while True:
        print('*' * 40)
        print('>> Select an option:')
        print(f'\t[1] rename --> Add duplicate file with a numbered filename.')
        print(f'\t[2] overwrite --> overwrite the existing file.')
        print(f'\t[3] cancel --> cancel the download.')
        print('*' * 40)
        c = input('Your choice: ').strip()
        if c == '1' or c == 'rename':
            return '1'
        if c == '2' or c == 'overwrite':
            return '2'
        if c == '3' or c == 'cancel':
            return '3'
        print('Invalid choice. Enter `1` or `2` or `3`.')


def user_prompt2():
    while True:
        print('*' * 40)
        print('>> Select an option:')
        print(f'\t[1] rename --> Add duplicate file with a numbered filename.')
        print(f'\t[2] resume --> resume file download.')
        print(f'\t[3] cancel --> cancel the download.')
        print('*' * 40)
        c = input('Your choice: ').strip()
        if c == '1' or c == 'rename':
            return '1'
        if c == '2' or c == 'resume':
            return '2'
        if c == '3' or c == 'cancel':
            return '3'
        print('Invalid choice. Enter `1` or `2` or `3`.')
