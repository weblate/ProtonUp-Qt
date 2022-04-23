# pupgui2 compatibility tools module
# Roberta
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os, shutil, tarfile, requests, hashlib
from PySide6.QtCore import *
from PySide6.QtWidgets import QMessageBox

CT_NAME = 'Roberta'
CT_LAUNCHERS = ['steam']
CT_DESCRIPTION = {}
CT_DESCRIPTION['en'] = '''Steam Play compatibility tool to run adventure games using native Linux ScummVM.'''
CT_DESCRIPTION['de'] = '''Steam Play Kompatibilitätstool, um Adventuregames mit Linux-nativer ScummVM zu spielen.'''
CT_DESCRIPTION['nl'] = '''Steam Play-compatibiliteitshulpmiddel voor het spelen van avonturengames met behulp van de Linux-versie van ScummVM.'''
CT_DESCRIPTION['pl'] = '''Narzędzie kompatybilności Steam Play do uruchamiania gier przygodowych poprzez natywny Linuksowy ScummVM.'''


class CtInstaller(QObject):
    
    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/dreamer/roberta/releases'
    CT_INFO_URL = 'https://github.com/dreamer/roberta/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
    
    def get_download_canceled(self):
        return self.p_download_canceled

    def set_download_canceled(self, val):
        self.p_download_canceled = val
    
    download_canceled = Property(bool, get_download_canceled, set_download_canceled)
    
    def __set_download_progress_percent(self, value : int):
        if self.p_download_progress_percent == value:
            return
        self.p_download_progress_percent = value
        self.download_progress_percent.emit(value)
    
    def __download(self, url, destination):
        """
        Download files from url to destination
        Return Type: bool
        """
        try:
            file = requests.get(url, stream=True)
        except OSError:
            return False
        
        self.__set_download_progress_percent(1) # 1 download started
        f_size = int(file.headers.get('content-length'))
        c_count = int(f_size / self.BUFFER_SIZE)
        c_current = 1
        destination = os.path.expanduser(destination)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as dest:
            for chunk in file.iter_content(chunk_size=self.BUFFER_SIZE):
                if self.download_canceled:
                    self.download_canceled = False
                    self.__set_download_progress_percent(-2) # -2 download canceled
                    return False
                if chunk:
                    dest.write(chunk)
                    dest.flush()
                self.__set_download_progress_percent(int(min(c_current / c_count * 98.0, 98.0))) # 1-98, 100 after extract
                c_current += 1
        self.__set_download_progress_percent(99) # 99 download complete
        return True
    
    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """
        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = requests.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if asset['name'].endswith('tar.xz'):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values
    
    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        if shutil.which('scummvm') and shutil.which('inotifywait'):
            return True
        msg = 'You need scummvm and inotify-tools for Roberta.\n\n'
        msg += 'scummvm: ' + str('missing' if shutil.which('scummvm') is None else 'found') + '\n'
        msg += 'inotify-tools: ' + str('missing' if shutil.which('inotifywait') is None else 'found')
        msg += '\n\nWill continue installing Roberta anyway.'
        QMessageBox.warning(None, 'Missing dependencies!', msg)
        return True  # install Roberta anyway

    def fetch_releases(self, count=100):
        """
        List available releases
        Return Type: str[]
        """
        tags = []
        for release in requests.get(self.CT_URL + '?per_page=' + str(count)).json():
            if 'tag_name' in release:
                tags.append(release['tag_name'])
        return tags

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False
        
        protondir = install_dir + 'roberta'

        destination = temp_dir
        destination += data['download'].split('/')[-1]
        destination = destination

        if not self.__download(url=data['download'], destination=destination):
            return False
        
        if os.path.exists(protondir):
            shutil.rmtree(protondir)
        tarfile.open(destination, "r:xz").extractall(install_dir)

        if os.path.exists(protondir):
            with open(os.path.join(protondir, 'VERSION.txt'), 'w') as f:
                f.write(version)
                f.write('\n')

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
