# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip. Designed for
use with Termux.

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

Termux users see [TERMUX.md](TERMUX.md) for more information on pymtheg on Termux.

[![demo](https://asciinema.org/a/473157.svg)](https://asciinema.org/a/473157)

## Installation

pymtheg requires Python 3.6.2 or later, and ffmpeg.

### From pip

```text
pip install pymtheg
```

### From main

```text
git clone https://github.com/markjoshwel/pymtheg.git
``````

You can then either use pip to install the dependencies from requirements.txt, or use Poetry instead.

## Quick Termux Setup

Copy the following command into the terminal:

```text
curl https://raw.githubusercontent.com/markjoshwel/pymtheg/main/termux-pymtheg-setup | sh
```

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] [-sda SDARGS] [-ffa FFARGS] [-cs CLIP_START] [-cl CLIP_LENGTH] [-ud] query

a python script to share songs from Spotify/YouTube as a 15 second clip

positional arguments:
  query                 song/link from spotify/youtube

options:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     directory to output to
  -o OUT, --out OUT     output file path, overrides directory arg
  -sda SDARGS, --sdargs SDARGS
                        args to pass to spotdl
  -ffa FFARGS, --ffargs FFARGS
                        args to pass to ffmpeg for clip creation
  -cs CLIP_START, --clip-start CLIP_START
                        clip start (default 0)
  -cl CLIP_LENGTH, --clip-length CLIP_LENGTH
                        length of output clip in seconds (default 15)
  -ud, --use-defaults   use 0 as clip start and --clip-length as clip end

ffargs default: '-hide_banner -loglevel error -c:a aac -c:v libx264 -pix_fmt yuv420p -tune stillimage -vf
scale='iw+mod(iw,2):ih+mod(ih,2):flags=neighbor''
```

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
