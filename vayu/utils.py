import cgi
import lxml.html
import re
from pathlib import Path
from urllib import parse

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
        fn = title.text + '.html'

    return _get_valid_filename(fn)


def get_filesize(resp):
    fs = resp.headers.get('content-length', None)
    return int(fs) if fs else fs


def get_category(filename):
    """
    Returns the category of file using its file extension
    Categories: Video, Music, Compresses, etc
    """
    ext = Path(filename).suffix.lstrip('.')
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
