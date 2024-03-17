# mk-scripts

A collection of misc scripts for my everyday tasks. Automation for Xcode and Flutter building processes, file management, archiving, logging, whatever.

Developed and used on macOS. An adaptation to other OS is required.

## Installation

### Add the library path to `PYTHONPATH`

**Sample for .zshrc**

```zsh
export PYTHONPATH="/Users/murad/dir1/../dirN/mk-scripts/python"
```

### Install modules

- [rich](https://pypi.org/project/rich/)
- [pync](https://pypi.org/project/pync/)
- [pillow](https://pypi.org/project/pillow/)

**Sample**

```zsh
python3.11 -m pip install rich pync pillow python-dateutil

```

### Sounds

Copy your favorite sounds as `MKError.{ext}` and `MKSuccess.{ext}` to `~/Library/Sounds`  