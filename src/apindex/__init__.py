#!/usr/bin/env python3

# Copyright (c) 2017 Ognjen Galic
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import base64
from pathlib import Path
import math
import os
import os.path
import time
from xml.dom.minidom import parseString


import importlib.resources
VERSION = '3.0.0'


class Icon:
    def __init__(self, file):
        self.file = file
        self.extensions = []


class ResourceManager:
    @staticmethod
    def getFile(fileName):
        return str(importlib.resources.files('apindex') / 'resources' / fileName)

    @staticmethod
    def readFile(fileName):
        with importlib.resources.files('apindex').joinpath('resources', fileName).open('r') as file:
            return file.read()

    @staticmethod
    def writeFile(filePath, data):
        with open(filePath, 'w') as file:
            file.write(data)

    @staticmethod
    def readFileBase64(fileName):
        with importlib.resources.files('apindex').joinpath('resources', fileName).open('rb') as file:
            data = file.read()
        return base64.b64encode(data).decode('ascii')

    @staticmethod
    def parseIconsDescription():
        doc = parseString(ResourceManager.readFile('icons.xml'))
        icons = []
        for icon in doc.getElementsByTagName('icon'):
            i = Icon(icon.getAttribute('file'))
            for ex in icon.getElementsByTagName('ex'):
                i.extensions.append(str(ex.firstChild.nodeValue))
            icons.append(i)
        return icons


class File:
    STATIC_FILE_HTML = ResourceManager.readFile('file.template.html')

    FILE_ICON = ResourceManager.readFileBase64('images/file.png')
    FOLDER_ICON = ResourceManager.readFileBase64('images/folder.png')
    BACK_ICON = ResourceManager.readFileBase64('images/back.png')

    ICONS = ResourceManager.parseIconsDescription()

    def getIcon(self):
        if self.filename == '..':
            return self.BACK_ICON

        if self.isDir():
            return self.FOLDER_ICON

        for icon in self.ICONS:
            for ex in icon.extensions:
                if self.filename.endswith(ex):
                    return ResourceManager.readFileBase64('images/' + icon.file)

        return self.FILE_ICON

    def __init__(self, filename, root='.'):
        filename = filename.rstrip('/')
        self.filename = File.stripCurrentDir(filename)
        self.root = File.stripCurrentDir(root)
        self.path = Path(root) / filename

    @staticmethod
    def stripCurrentDir(path):
        return path.replace('./', '').replace('/.', '')

    def toHTML(self):
        if self.isDir():
            fileSize = '-'
        else:
            fileSize = str(math.floor(os.path.getsize(self.path) / 1000)) + ' kB'
        modifyTime = time.strftime(
            '%d-%b-%Y %H:%M', time.localtime(os.path.getmtime(self.path))
        )

        return (
            File.STATIC_FILE_HTML.replace('#FILENAME', self.path.name)
            .replace('#FILEURL', self.filename)
            .replace('#MODIFIED', modifyTime)
            .replace('#SIZE', fileSize)
            .replace('#IMAGE', self.getIcon())
        )

    def getPath(self):
        return File.stripCurrentDir(self.root + '/' + self.filename)

    def getPathFromRoot(self):
        if self.filename == '.':
            return '/'
        else:
            return '/' + self.getPath()

    def getFileName(self):
        return self.filename

    def isDir(self):
        return os.path.isdir(self.path)

    def getChildren(self):
        for file in os.listdir(self.filename):
            yield File(file, self.getPath())

    def getParentDir(self):
        return self.root


class IndexWriter:
    STATIC_FOOTER = ResourceManager.readFile('footer.template.html').replace(
        '#VERSION', VERSION
    )

    @staticmethod
    def writeIndex(startPath, title=None, footer=None, ignore=[], is_root_dir=False):
        filesRead = []
        dirsRead = []
        files_to_ignore = set(Path(file) for file in ignore)
        root = File(Path(startPath).as_posix().rstrip('/'))
        html = ResourceManager.readFile('index.template.html')

        if title is None:
            title = root.getPathFromRoot()
        if footer is None:
            footer = IndexWriter.STATIC_FOOTER

        # fill the details
        html = html.replace('#TITLE', title)
        html = html.replace('#FOOTER', footer)
        html = html.replace('#DIR', root.getPathFromRoot())

        for file in root.getChildren():
            if file.path in files_to_ignore:
                continue
            # we do not want to index the index itself
            if file.getFileName() == 'index.html':
                continue

            if file.isDir():
                dirsRead.append(file.toHTML())
                IndexWriter.writeIndex(file.getPath(), title=file.getPathFromRoot())
            else:
                try:
                    filesRead.append(file.toHTML())
                except FileNotFoundError as e:
                    print(f'could not find file {e}')

        # fill in the file list
        dirsRead.sort()
        filesRead.sort()
        BACK_DIR = '' if is_root_dir else File('..').toHTML()
        html = html.replace('#GEN_DIRS', BACK_DIR + ''.join(dirsRead))
        html = html.replace('#GEN_FILES', ''.join(filesRead))

        # write the actual index file
        print('Writing ' + root.getPath() + '/index.html')
        ResourceManager.writeFile(root.getPath() + '/index.html', html)


def main():
    parser = argparse.ArgumentParser(description='apindex')
    parser.add_argument(
        '--ignore',
        default=[],
        nargs='*',
        help='files or paths to ignore',
    )
    parser.add_argument(
        '--ignore_hidden',
        default=False,
        help='ignore files that start with .',
    )
    parser.add_argument('root_dir', help='root directory to index')
    args = parser.parse_args()
    IndexWriter.writeIndex(args.root_dir, ignore=args.ignore, is_root_dir=True)


if __name__ == '__main__':
    main()
