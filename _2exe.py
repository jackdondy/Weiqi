import os

import PyInstaller.__main__

PyInstaller.__main__.run([
    'WeiQi.py',
    # '--onefile',
    '--add-data=WeiQiSrc\\*' + os.pathsep + 'WeiQiSrc',
    '--windowed',
    '-y'
])