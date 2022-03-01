# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip. Designed for
use with Termux.

See the [repository](https://github.com/markjoshwel/pymtheg) for more installation and
contribution instructions/information.

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] [-sda SDARGS] [-ffa FFARGS] [-cl CLIP_LENGTH] [-ud] query

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
  -cl CLIP_LENGTH, --clip-length CLIP_LENGTH
                        length of output clip in seconds (default 15)
  -ud, --use-defaults   use 0 as clip start and --clip-length as clip end
```

**Notes:**

- ffargs default:
  `-hide_banner -loglevel error -loop 1 -c:a aac -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -tune stillimage -shortest`

## License

pymtheg is unlicensed with The Unlicense. In short, do whatever. You can find copies of
the license in the
[UNLICENSE](https://github.com/markjoshwel/pymtheg/blob/main/UNLICENSE) file or in the
[pymtheg module docstring](https://github.com/markjoshwel/pymtheg/blob/main/pymtheg.py#L5).
