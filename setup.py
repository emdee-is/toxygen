from setuptools import setup
from setuptools.command.install import install
from platform import system
from subprocess import call
import main
import sys
import os
from utils.util import curr_directory, join_path


version = main.__version__ + '.0'


if system() == 'Windows':
    MODULES = ['PyQt5', 'PyAudio', 'numpy', 'opencv-python', 'pydenticon', 'cv2']
else:
    MODULES = ['pydenticon']
    MODULES.append('PyQt5')
    try:
        import pyaudio
    except ImportError:
        MODULES.append('PyAudio')
    try:
        import numpy
    except ImportError:
        MODULES.append('numpy')
    try:
        import cv2
    except ImportError:
        MODULES.append('opencv-python')
    try:
        import coloredlogs
    except ImportError:
        MODULES.append('coloredlogs')
    try:
        import pyqtconsole
    except ImportError:
        MODULES.append('pyqtconsole')


def get_packages():
    directory = join_path(curr_directory(__file__), 'toxygen')
    for root, dirs, files in os.walk(directory):
        packages = map(lambda d: 'toxygen.' + d, dirs)
        packages = ['toxygen'] + list(packages)
        return packages

class InstallScript(install):
    """This class configures Toxygen after installation"""

    def run(self):
        install.run(self)
        try:
            if system() != 'Windows':
                call(["toxygen", "--clean"])
        except:
            try:
                params = list(filter(lambda x: x.startswith('--prefix='), sys.argv))
                if params:
                    path = params[0][len('--prefix='):]
                    if path[-1] not in ('/', '\\'):
                        path += '/'
                    path += 'bin/toxygen'
                    if system() != 'Windows':
                        call([path, "--clean"])
            except:
                pass


setup(name='Toxygen',
      version=version,
      description='Toxygen - Tox client',
      long_description='Toxygen is powerful Tox client written in Python3',
      url='https://git.macaw.me/emdee/toxygen/',
      keywords='toxygen Tox messenger',
      author='Ingvar',
      maintainer='',
      license='GPL3',
      packages=get_packages(),
      install_requires=MODULES,
      include_package_data=True,
      classifiers=[
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.9',
      ],
      entry_points={
          'console_scripts': ['toxygen=toxygen.main:main']
      },
      cmdclass={
          'install': InstallScript
      },
      zip_safe=False
      )
