# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip.
[Designed for use with Termux.](https://github.com/markjoshwel/pymtheg/blob/main/TERMUX.md)

See the [repository](https://github.com/markjoshwel/pymtheg) for more installation and
contribution instructions/information.

[![asciicast](https://asciinema.org/a/473914.svg)](https://asciinema.org/a/473914)

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] [-sda SDARGS] [-ffa FFARGS] [-cs CLIP_START] [-ce CLIP_END] [-i IMAGE] [-ud] [-y] query

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
                        specify clip start (default 0)
  -ce CLIP_END, --clip-end CLIP_END
                        specify clip end (default +15)
  -i IMAGE, --image IMAGE
                        specify custom image
  -ud, --use-defaults   use 0 as clip start and --clip-length as clip end
  -y, --yes             say yes to every y/n prompt

ffargs default: "-hide_banner -loglevel error -c:a aac -c:v libx264 -pix_fmt yuv420p -tune stillimage -vf scale='iw+mod(iw,2):ih+mod(ih,2):flags=neighbor'"
```

## License

pymtheg is unlicensed with The Unlicense. In short, do whatever. You can find copies of
the license in the
[UNLICENSE](https://github.com/markjoshwel/pymtheg/blob/main/UNLICENSE) file or in the
[pymtheg module docstring](https://github.com/markjoshwel/pymtheg/blob/main/pymtheg.py#L5).
