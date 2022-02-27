# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip. Designed for
use with Termux.

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

pymtheg requires Python 3.6.2 or later.

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

Write the following into `$HOME/bin/termux-url-opener`.

```text
#!/bin/bash

pymtheg $1 -d ~/storage/movies/pymtheg/
```

Alternatively, you can run the following command to obtain the script:

```text
curl https://raw.githubusercontent.com/markjoshwel/pymtheg/main/termux-url-opener -o $HOME/bin/termux-url-opener
```

**Notes:**

- This assumes you have no `$HOME/bin/termux-url-opener` script. If you do, you may have
 to tailer the following instructions to work with your current setup.

- This also assumes that you already have a folder named `pymtheg` in the `Movies`
  folder of your internal storage, and that you have already ran `termux-setup-storage`
  to allow access of your internal storage from within Termux. If not, simply adjust the
  script shown above accordingly.

- If you did not install pymtheg through pip, change `pymtheg` to the path leading to
  `pymtheg.py`, such as `~/scripts/pymtheg.py`.

- If you have a copy of the repo and use Poetry, change `pymtheg` to
  `poetry run pymtheg`. However do add a line before the pymtheg invocation to change
  directories to the repository root or else the `poetry run` invocation will fail.

- Dont forget to `chmod +x` the script after writing!

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] [-sda SDARGS] [-cl CLIP_LENGTH] query

a python script to share songs from Spotify/YouTube as a 15 second clip

positional arguments:
  query                 song/link from spotify/youtube

options:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     directory to output to
  -o OUT, --out OUT     output file path, overrides directory arg
  -sda SDARGS, --sdargs SDARGS
                        args to pass to spotdl
  -cl CLIP_LENGTH, --clip-length CLIP_LENGTH
                        length of output clip in seconds (default 15)
```

As pymtheg is built around [spotDL](https://github.com/spotDL/spotify-downloader), you
can pass spotDL args to pymtheg. See their documentation for more information!

### Return Codes

- `0`: Successfull
- `1`: Invalid args
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
