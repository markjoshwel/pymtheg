# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip. Designed for
use with Termux.

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

### From pip

```text
pip install pymtheg
```

### From main

```text
git clone https://github.com/markjoshwel/pymtheg.git
``````

You can then either use pip to install the dependencies from requirements.txt, or use Poetry instead.

### Additional Setup for Termux

This assumes you have no `$HOME/bin/termux-url-opener` script. If you do, you may have to
tailer the following instructions to work with your current setup.

This also assumes that you already have a folder named `pymtheg` in the `Movies` folder
of your internal storage, and that you have already ran `termux-setup-storage` to allow
access of your internal storage from within Termux. If not, simply adjust the script
shown below accordingly.

```text
#!/bin/bash

pymtheg $1 -d ~/storage/movies/pymtheg/
```

If you did not install pymtheg through pip, change `pymtheg` to the path leading to
`pymtheg.py`, such as `~/scripts/pymtheg.py`.

If you have a copy of the repo and use Poetry, change `pymtheg` to `poetry run pymtheg`.
However do add a line before the pymtheg invocation to change directories to the
repository root or else the `poetry run` invocation will fail.

Dont forget to `chmod +x` the script after writing.

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] link

a python script to share songs from Spotify/YouTube as a 15 second clip

positional arguments:
  link               spotify or youtube link

optional arguments:
  -h, --help         show this help message and exit
  -d DIR, --dir DIR  directory to output to
  -o OUT, --out OUT  output file path, overrides directory arg
```

### Return Codes

- `0`: Successfull

- `1`: Invalid link

- `2`: Error during song retrieval

- `3`: Error during video creation

## Contributing

When contributing your first changes, please include an empty commit for copyright waiver
using the following message (replace 'John Doe' with your name or nickname):

```text
John Doe Copyright Waiver

I dedicate any and all copyright interest in this software to the
public domain.  I make this dedication for the benefit of the public at
large and to the detriment of my heirs and successors.  I intend this
dedication to be an overt act of relinquishment in perpetuity of all
present and future rights to this software under copyright law.
```

The command to create an empty commit from the command-line is:

```shell
git commit --allow-empty
```

## License

pymtheg is unlicensed with The Unlicense. In short, do whatever. You can find copies of
the license in the [UNLICENSE](UNLICENSE) file or in the
[pymtheg module docstring](pymtheg.py).
