# pymtheg

A Python script to share songs from Spotify/YouTube as a 15 second clip.
[Designed for use with Termux.](https://github.com/markjoshwel/pymtheg/blob/main/TERMUX.md)

See the [repository](https://github.com/markjoshwel/pymtheg) for more installation and
contribution instructions/information.

[![asciicast](https://asciinema.org/a/483803.svg)](https://asciinema.org/a/483803)

## Installation

pymtheg requires [Python 3.6.2](https://python.org/) or later, and
[ffmpeg](https://ffmpeg.org/).

## Usage

```text
usage: pymtheg [-h] [-d DIR] [-o OUT] [-tf TIMESTAMP_FORMAT] [-e EXT] [-sda SDARGS] [-ffa FFARGS]
               [-cs CLIP_START] [-ce CLIP_END] [-i IMAGE] [-ud] [-y]
               queries [queries ...]

a python script to share songs from Spotify/YouTube as a 15 second clip

positional arguments:
  queries               song queries (see querying)

options:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     directory to output to, formattable (see formatting)
  -o OUT, --out OUT     output file name format, formattable (see formatting)
  -tf TIMESTAMP_FORMAT, --timestamp-format TIMESTAMP_FORMAT
                        timestamp format, formattable (see formatting)
  -e EXT, --ext EXT     file extension, defaults to "mp4"
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

querying:
  queries are passed onto spotdl, and thus must be any one of the following:
    1. text
      "<query>"
      e.g. "thundercat - them changes"
    2. spotify track/album url
      "<url>"
      e.g. "https://open.spotify.com/track/..."
    3. youtube source + spotify metadata
      "<youtube url>|<spotify url>"
      e.g. "https://www.youtube.com/watch?v=...|https://open.spotify.com/track/..."

argument defaults:
  -f, --ffargs:
    "-hide_banner -loglevel error -c:a aac -c:v libx264 -pix_fmt yuv420p -tune stillimage -vf scale='iw+mod(iw,2):ih+mod(ih,2):flags=neighbor'"
  -o, --out:
    "{artists} - {title}"
  -t, --timestamp-format:
     ({cs}{cer})

formatting:
  available placeholders:
    from spotdl:
      {artist}, {artists}, {title}, {album}, {playlist}
    from pymtheg:
      {cs}
        clip end as per [(h*)mm]ss, e.g. 10648 (1h, 06m, 48s)
      {css}
        clip end in seconds, e.g. 4008 (1h, 6m, 48s -> 4008s)
      {ce}
        clip end as per [(h*)mm]ss, e.g. 10703 (1h, 07m, 03s)
      {ces}
        clip end in seconds, e.g. 4023 (1h, 07m, 03s -> 4023s)
      {cer}
        e.g. +15
    
      notes:
        1. pymtheg placeholders can only be used with `-tf, --timestamp-format`
        2. "[(h*)mm]ss": seconds and minutes will always be represented as 2
           digits and will be right adjusted with 0s if needed, however hours
           can be represented by any number of characters, e.g. "1" or "123456"
```

### Examples

1. Get a song through a Spotify link

   ```text
   pymtheg "https://open.spotify.com/track/7CH99b2i1TXS5P8UUyWtnM"
   ```

2. Get a song through a search query

   ```text
   pymtheg "thundercat - them changes"
   ```

3. Get multiple songs through multiple queries

   ```text
   pymtheg "https://open.spotify.com/track/7CH99b2i1TXS5P8UUyWtnM" "silk sonic blast off"
   ```

4. Same as 1, however you set the clip start to random and let pymtheg suprise you

   ```text
   pymtheg "https://open.spotify.com/track/7CH99b2i1TXS5P8UUyWtnM" -cs "*" -ce "+15" --use-defaults
   ```

## License

pymtheg is unlicensed with The Unlicense. In short, do whatever. You can find copies of
the license in the
[UNLICENSE](https://github.com/markjoshwel/pymtheg/blob/main/UNLICENSE) file or in the
[pymtheg module docstring](https://github.com/markjoshwel/pymtheg/blob/main/pymtheg.py#L5).
