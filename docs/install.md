# How to install Toxygen

### Linux

1. Install [c-toxcore](https://github.com/TokTok/c-toxcore/)
2. Install PortAudio: 
``sudo apt-get install portaudio19-dev``
3. For 32-bit Linux install PyQt5: ``sudo apt-get install python3-pyqt5``
4. Install [OpenCV](http://docs.opencv.org/trunk/d7/d9f/tutorial_linux_install.html) or via ``sudo pip3 install opencv-python``
5. Install [toxygen](https://git.plastiras.org/emdee/toxygen/)
6. Run toxygen using ``toxygen`` command.

## From source code (recommended for developers)

### Windows

Note: 32-bit Python isn't supported due to bug with videocalls. It is strictly recommended to use 64-bit Python.

1. [Download and install latest Python 3 64-bit](https://www.python.org/downloads/windows/)
2. Install PyQt5: ``pip install pyqt5``
3. Install PyAudio: ``pip install pyaudio``
4. Install numpy: ``pip install numpy``
5. Install OpenCV: ``pip install opencv-python``
6. [Download toxygen](https://github.com/toxygen-project/toxygen/archive/master.zip)
7. Unpack archive
8. Download latest libtox.dll build, download latest libsodium.a build, put it into \toxygen\libs\
9. Run \toxygen\main.py.

### Linux

1. Install latest Python3: 
``sudo apt-get install python3``
2. Install PyQt5: ``sudo apt-get install python3-pyqt5`` or ``sudo pip3 install pyqt5``
3. Install [toxcore](https://github.com/TokTok/c-toxcore) with toxav support)
4. Install PyAudio: 
``sudo apt-get install portaudio19-dev`` and ``sudo apt-get install python3-pyaudio`` (or ``sudo pip3 install pyaudio``)
5. Install NumPy: ``sudo pip3 install numpy``
6. Install [OpenCV](http://docs.opencv.org/trunk/d7/d9f/tutorial_linux_install.html) or via ``sudo pip3 install opencv-python``
7. [Download toxygen](https://git.plastiras.org/emdee/toxygen/)
8. Unpack archive
9. Run app:
``python3 main.py``

Optional: install toxygen using setup.py: ``python3 setup.py install``
