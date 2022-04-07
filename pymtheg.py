"""
pymtheg: A Python script to share songs from Spotify/YouTube as a 15 second clip

--------------------------------------------------------------------------------

This is free and unencumbered software released into the public domain.

-----------------------------------------------------------------------

Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software,
either in source code form or as a compiled binary, for any purpose, commercial or
non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors of this software
dedicate any and all copyright interest in the software to the public domain. We make
this dedication for the benefit of the public at large and to the detriment of our heirs
and successors. We intend this dedication to be an overt act of relinquishment in
perpetuity of all present and future rights to this software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
"""

from typing import Iterable, List, Literal, NamedTuple, Optional, Tuple, Union

from argparse import ArgumentParser, RawTextHelpFormatter
from tempfile import TemporaryDirectory
from traceback import print_tb
from datetime import datetime
from random import randint
from pathlib import Path
from shutil import move
from json import loads
import subprocess

from rich.console import Console


FFARGS: str = (
    "-hide_banner -loglevel error -c:a aac -c:v libx264 -pix_fmt yuv420p "
    "-tune stillimage -vf scale='iw+mod(iw,2):ih+mod(ih,2):flags=neighbor'"
)
OUT: str = "{artists} - {title}"
TIMESTAMP_FORMAT: str = " ({cs}{cer})"
CLIP_START: str = "0"
CLIP_END: str = "+15"

premsg_info = "[dim]pymtheg: [/dim][bold cyan]info[/bold cyan][dim]:[/]"
premsg_error = "[dim]pymtheg: [/dim][bold red]error[/bold red][dim]:[/]"


class Timestamp(NamedTuple):
    """
    timestamp named tuple

    type: Literal[0] | Literal[1]
        0 if start timestamp; 1 if end timestamp
    ss: int
        timestamp in seconds
    random: bool
        is timestamp random
    relative: bool = False
        is timestamp relative
    """

    type: Union[Literal[0], Literal[1]]
    ss: int
    random: bool = False
    relative: bool = False

    def __str__(self) -> str:
        return ("+" if self.relative else "") + str(self.ss)


class Behaviour(NamedTuple):
    """typed command line argument tuple"""

    queries: List[str]
    dir: Path
    out: str
    timestamp_format: str
    ext: str
    sdargs: List[str]
    ffargs: List[str]
    clip_start: Timestamp
    clip_end: Timestamp
    image: Optional[Path]
    use_defaults: bool
    yes: bool


def main() -> None:
    """pymtheg entry point"""
    console = Console()
    bev = get_args(console)

    # make tempdir
    with TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)

        # download songs
        with console.status(f"[dim]downloading songs...[/]", spinner="arc"):
            spotdl_proc = invocate(
                console=console,
                name="spotdl",
                args=bev.queries + ["--path-template", f"{bev.out}.{{ext}}"] + bev.sdargs,
                cwd=tmpdir,
                errcode=2,
                capture_output=True,
            )

        # process songs
        processed = 0

        for song_path in tmpdir.rglob("*.*"):
            # ensure that file was export of spotDL (list from spotdl -h)
            if song_path.suffix not in [".m4a", ".ogg", ".flac", ".mp3", ".wav", ".opus"]:
                continue

            # duration retrieval
            with console.status(f"[dim]status: probe song duration[/]", spinner="arc"):
                proc = invocate(
                    console=console,
                    name="ffprobe",
                    args=[
                        "-print_format",
                        "json",
                        "-show_entries",
                        "format=duration",
                        song_path,
                    ],
                    capture_output=True,
                )
                song_duration: int = int(
                    loads(proc.stdout)["format"]["duration"].split(".")[0]
                )

            if processed == 0:
                # print timestamp format/using default message on first song
                if bev.use_defaults:
                    console.print(
                        f'{premsg_info} using defaults, clip start is "{bev.clip_start}"'
                        f' and clip end is "{bev.clip_end}"\n'
                    )

                else:
                    console.print(f"{premsg_info} enter timestamps in format \[hh:mm:]ss")
                    console.print('               timestamp can be "*" for random')
                    console.print(
                        '               end timestamp can be relative, prefix with "+"'
                    )
                    console.print(
                        f"               press enter to use given defaults "
                        f'("{bev.clip_start}", "{bev.clip_end}")\n'
                    )

            console.print(f"- [bold]{song_path.stem}[/] ({to_timestamp(song_duration)})")

            # generate query/info messages
            _msg_format = "    {}: "
            _query_clip_end = f"clip end ({bev.clip_end})"
            _query_clip_start = f"clip start ({bev.clip_start})"
            _query_new_filename = "filename"
            _info_status = "status"
            _info_notice = "notice"
            _longest_msg_len = len(
                max(
                    _query_new_filename,
                    _query_clip_end,
                    _query_clip_start,
                    _info_status,
                    _info_notice,
                    key=len,
                )
            )

            query_clip_end = _msg_format.format(
                _query_clip_end.rjust(_longest_msg_len),
            )
            query_clip_start = _msg_format.format(
                _query_clip_start.rjust(_longest_msg_len),
            )
            query_new_filename = _msg_format.format(
                _query_new_filename.rjust(_longest_msg_len),
            )
            info_status = _msg_format[2:].format(
                _info_status.rjust(_longest_msg_len),
            )
            info_notice = _msg_format.format(_info_notice.rjust(_longest_msg_len))
            indent = len(_msg_format) - 2 + _longest_msg_len

            # construct working paths
            song_path = song_path.absolute()
            song_clip_path = tmpdir.joinpath(f"{song_path.stem}_clip.mp3").absolute()
            song_cover_path = tmpdir.joinpath(f"{song_path.stem}_cover.png").absolute()
            video_clip_path = tmpdir.joinpath(f"{song_path.stem}_clip.mp4").absolute()

            # get timestamps
            start_timestamp, end_timestamp = parse_timestamps(
                bev.clip_start, bev.clip_end, duration=song_duration
            )

            if bev.clip_end.relative:
                end_timestamp += start_timestamp

            if end_timestamp == -1:
                end_timestamp = song_duration

            if not bev.use_defaults:
                # timestamp prompt
                while True:
                    _start_timestamp: Optional[Timestamp] = None
                    _end_timestamp: Optional[Timestamp] = None

                    # starting timestamp
                    while True:
                        cs_response = input(query_clip_start)

                        if cs_response != "":
                            _start_timestamp = check_timestamp(0, cs_response)

                            if _start_timestamp is None:
                                # invalid format
                                console.print(
                                    "[dim][red]"
                                    + (" " * indent)
                                    + ("^" * len(cs_response))
                                    + "[/dim][bold] invalid timestamp",
                                )

                            else:
                                if _start_timestamp.ss > song_duration:
                                    # invalid, timestamp >= song duration
                                    console.print(
                                        "[dim][red]"
                                        + (" " * indent)
                                        + ("^" * len(cs_response))
                                        + "[/dim][bold] timestamp exceeds song duration",
                                    )

                                else:
                                    break

                        else:
                            _start_timestamp = bev.clip_start
                            break

                    # ending timestamp
                    while True:
                        ce_response = input(query_clip_end)

                        if ce_response != "":
                            _end_timestamp = check_timestamp(1, ce_response)

                            if _end_timestamp is None:
                                # invalid format
                                console.print(
                                    "[dim][red]"
                                    + (" " * indent)
                                    + ("^" * len(cs_response))
                                    + "[/dim][bold] invalid timestamp",
                                )

                            else:
                                break

                        else:
                            _end_timestamp = bev.clip_end
                            break

                    assert isinstance(_start_timestamp, Timestamp)  # type: ignore
                    assert isinstance(_end_timestamp, Timestamp)  # type: ignore

                    # parse timestamps
                    start_timestamp, end_timestamp = parse_timestamps(
                        _start_timestamp, _end_timestamp, duration=song_duration
                    )

                    # confirm timestamps
                    if bev.yes:
                        break

                    # dont prompt confirmation if defaults were used
                    if not (cs_response == "" and ce_response == ""):
                        console.print(
                            "{premsg}clip duration: {start} -> {end} ({duration}s)".format(
                                premsg=info_notice,
                                start=to_timestamp(start_timestamp),
                                end=to_timestamp(end_timestamp),
                                duration=end_timestamp - start_timestamp,
                            )
                        )
                        confirmation_response = input(
                            f"{' ' * indent}confirm? [y/n] (y) "
                        ).lower()

                        if confirmation_response == "y" or confirmation_response == "":
                            break

                        else:
                            pass

                    else:
                        break

            elif start_timestamp > song_duration:
                console.print(f"{info_notice}skipping song")
                processed += 1
                break

            # construct and confirm output path
            out_path: Path = bev.dir.joinpath(
                "{name}{timestamp}.{ext}".format(
                    name=song_path.stem,
                    timestamp=tf_format(
                        string=bev.timestamp_format,
                        clip_start=start_timestamp,
                        clip_end=end_timestamp,
                    ),
                    ext=bev.ext,
                )
            ).absolute()

            if (
                # no -o specified and out_path exists
                out_path.exists()
                and bev.yes is False
            ):
                console.print(f'{info_notice}"{out_path.name}" exists in output dir.')
                overwrite_response = input(
                    f"{' ' * indent}overwrite? ([y]es/[n]o/[c]hange) "
                ).lower()

                if overwrite_response == "y":
                    pass

                elif overwrite_response == "c":
                    while True:
                        new_filename_response = input(query_new_filename)
                        new_out_path = Path(new_filename_response)
                        if new_out_path.exists():
                            console.print(
                                (" " * indent) + ("^" * len(new_filename_response)),
                                "file already exists",
                            )
                        else:
                            out_path = new_out_path
                            break

                else:
                    console.print(f"{info_notice}skipping song")
                    processed += 1
                    break

            # clip audio
            with console.status(f"[dim]{info_status}clip audio[/]", spinner="arc"):
                invocate(
                    console=console,
                    name="ffmpeg",
                    args=[
                        "-ss",
                        str(start_timestamp),
                        "-to",
                        str(end_timestamp),
                        "-i",
                        song_path,
                        song_clip_path,
                    ],
                    cwd=tmpdir,
                    errcode=3,
                    capture_output=True,
                )

            # get album art if needed
            if bev.image is None:  # no custom image was specified
                with console.status(f"[dim]{info_status}get album art[/]", spinner="arc"):
                    invocate(
                        console=console,
                        name="ffmpeg",
                        args=[
                            "-i",
                            song_path,
                            "-an",
                            song_cover_path,
                        ],
                        cwd=tmpdir,
                        errcode=3,
                        capture_output=True,
                    )

            else:
                song_cover_path = bev.image

            # create clip
            with console.status(f"[dim]{info_status}create clip[/]", spinner="arc"):
                invocate(
                    console=console,
                    name="ffmpeg",
                    args=[
                        "-loop",
                        "1",
                        "-i",
                        song_cover_path,
                        "-i",
                        song_clip_path,
                        "-t",
                        str(end_timestamp - start_timestamp),
                        *bev.ffargs,
                        video_clip_path,
                    ],
                    errcode=3,
                )

                move(str(video_clip_path), str(out_path))

            processed += 1

    if processed > 0:
        console.print(
            f"\n{premsg_info} all operations successful. have a great {part_of_day()}."
        )

    else:
        if spotdl_proc.stdout != "":
            console.print(f"\n{premsg_error} invocation stdout:\n{spotdl_proc.stdout}")
        if spotdl_proc.stderr != "":
            console.print(f"\n{premsg_error} invocation stderr:\n{spotdl_proc.stderr}")

        console.print(
            f"{premsg_error} invalid link/query, nothing to do. (see above for more information)"
        )
        exit(1)


def part_of_day() -> str:
    """
    used to greet user goodbye

    call it bloat or whatever, i like it
    """
    hh = datetime.now().hour
    return (
        "morning ahead"
        if 5 <= hh <= 11
        else "afternoon ahead"
        if 12 <= hh <= 19
        else "evening ahead"
        if 18 <= hh <= 22
        else "night"
    )


def check_timestamp(type: Union[Literal[0], Literal[1]], ts: str) -> Optional[Timestamp]:
    """
    checks timestamps for timestamp retrieval and command line argument validation

    ts: str
        timestamp string
    type: Literal[0] | Literal[1]
        0 if start timestamp; 1 if end timestamp

    returns a Timestamp object if check was successful else None
    """
    ts = ts.strip()

    if ts == "*":
        return Timestamp(type=type, ss=0, random=True)

    elif ts == "-1":
        return Timestamp(type=type, ss=-1)

    else:
        relative: bool
        if ts.startswith("+"):
            if type == 0:  # relative timestamps in start timestamp are not allowed
                return None

            relative = True
            ts = ts[1:]

        else:
            relative = False

        sts = ts.split(":")  # split time stamp (hh:mm:ss)
        sts.reverse()  # (ss:mm:hh)

        tu_conv = [1, 60, 3600]  # time unit conversion
        total_ss = 0  # total seconds

        if len(sts) < 4:
            for tu, tu_c in zip(sts, tu_conv):
                if tu.isnumeric():
                    total_ss += int(tu) * tu_c

                else:
                    return None

            return Timestamp(type=type, ss=total_ss, relative=relative)

        else:
            return None


def parse_timestamps(start: Timestamp, end: Timestamp, duration: int) -> Tuple[int, int]:
    """
    parses start timestamp and end timestamp into absolute seconds

    start: Timestamp
        start timestamp
    end: Timestamp
        end timestamp
    duration: int
        song duration in seconds

    returns song start and song end respectively, in seconds
    """
    ts_start: int
    ts_end: int

    if start.random and end.random:
        ts_start = randint(0, duration)
        ts_end = randint(ts_start, duration)

    elif start.random:
        ensure_random = end.ss if end.relative else 0
        ts_start = randint(0, duration - ensure_random)
        ts_end = ts_start + end.ss

    elif end.random:
        ts_start = start.ss
        ts_end = randint(start.ss, duration)

    else:
        ts_start = start.ss
        ts_end = (start.ss + end.ss) if end.relative else end.ss

    return (ts_start, ts_end)


def to_timestamp(ts: int) -> str:
    """returns a [(h*):mm:]ss timestamp string from `ts: int`"""
    _mm = ts // 60
    hh = _mm // 60
    mm = _mm - hh * 60
    ss = ts % 60

    return ":".join(
        [str(u).rjust(2, "0") for u in (hh, mm) if u != 0] + [str(ss).rjust(2, "0")]
    ).lstrip("0")


def tf_format(string: str, clip_start: int, clip_end: int) -> str:
    """
    formats a string with clip information, returns result

    clip_start: int
        clip start in seconds
    clip_end: int
        clip end in seconds
    """

    def ts_format(ts: int) -> str:
        """nested function represent `ts: int` as [(h*)mm]ss, returns result"""
        _mm = ts // 60
        hh = _mm // 60
        mm = _mm - hh * 60
        ss = ts % 60

        result = ""

        for index, unit in enumerate([ss] + [u for u in (mm, hh) if u != 0]):
            if index < 2:  # ss or mm
                result = str(unit).rjust(2, "0") + result
            else:
                result = str(unit) + result

        return result.lstrip("0")

    replaceables = (
        ("{cs}", ts_format(clip_start)),
        ("{css}", clip_start),
        ("{ce}", ts_format(clip_end)),
        ("{ces}", clip_end),
        ("{cer}", f"+{clip_end - clip_start}"),
    )

    for placeholder, value in replaceables:
        if placeholder in string:
            string = string.replace(placeholder, str(value))

    return string


def invocate(
    console: Console,
    name: str,
    args: Iterable[Optional[Union[str, Path]]] = [],
    cwd: Optional[Path] = None,
    errcode: int = -1,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """
    invocates command using subprocess.run

    name: str,
        name of program
    args: Iterable[Optional[Union[str, Path]]] = [],
        args of program, e.g. ["download", "-o=$HOME"]
    cwd: Optional[Path] = None,
        working directory for process to be run
    errcode: int = -1,
        exit code for if the process returns non-zero
    capture_output: bool = False,
        maps to subprocess.run(capture_output=); captures stdout and stderr
    """

    invocation: List[Union[str, Path]] = [name]

    for arg in args:
        if arg is not None:
            invocation.append(arg)

    try:
        proc = subprocess.run(
            invocation,
            cwd=cwd,
            universal_newlines=True,
            capture_output=capture_output,
        )

        if proc.returncode != 0:
            if capture_output:
                if proc.stdout != "":
                    console.print(f"\n{premsg_error} invocation stdout:\n{proc.stdout}")
                if proc.stderr != "":
                    console.print(f"\n{premsg_error} invocation stderr:\n{proc.stderr}")

            console.print(
                f"\n{premsg_error} error during invocation of "
                f"'{' '.join([str(p) for p in invocation])}', returned non-zero exit "
                f"code {proc.returncode}, see above for details"
            )
            exit(proc.returncode)

    except FileNotFoundError as err:
        print_tb(err.__traceback__)
        console.print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"{premsg_error} could not invocate {name}, see traceback"
        )
        exit(errcode)

    except Exception as err:
        print_tb(err.__traceback__)
        console.print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"{premsg_error} unknown error during invocation of {name}, see traceback"
        )
        exit(errcode)

    else:
        return proc


def get_args(console: Console) -> Behaviour:
    """parse and validate arguments"""
    # parse
    parser = ArgumentParser(
        prog="pymtheg",
        description=(
            "a python script to share songs from Spotify/YouTube as a 15 second clip"
        ),
        epilog=f"""querying:
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
    "{FFARGS}"
  -o, --out:
    "{OUT}"
  -t, --timestamp-format:
    "{TIMESTAMP_FORMAT}"

formatting:
  available placeholders:
    from spotdl:
      {{artist}}, {{artists}}, {{title}}, {{album}}, {{playlist}}
    from pymtheg:
      {{cs}}
        clip end as per [(h*)mm]ss
        e.g. 10648 (1h, 06m, 48s)
      {{css}}
        clip end in seconds
        e.g. 4008 (1h, 6m, 48s -> 4008s)
      {{ce}}
        clip end as per [(h*)mm]ss, e.g. 10703 (1h, 07m, 03s)
      {{ces}}
        clip end in seconds
        e.g. 4023 (1h, 07m, 03s -> 4023s)
      {{cer}}
        clip end relative to clip start, prefixed with +
        e.g. +15
    
      notes:
        1. pymtheg placeholders can only be used with `-tf, --timestamp-format`
        2. "[(h*)mm]ss": seconds and minutes will always be represented as 2
           digits and will be right adjusted with 0s if needed, unless they are
           the first shown unit where they may have up to two characters. hours
           can be represented by any number of characters.
           e.g. "138:02:09", "1:59:08", "2:05", "6"

examples:
  1. get a song through a spotify link
    pymtheg "https://open.spotify.com/track/..."
  2. get a song through a search query
    pymtheg "thundercat - them changes"
  3. get multiple songs through multiple queries
    pymtheg "https://open.spotify.com/track/..." "<query 2>"
  4. get a random 15s clip of a song
    pymtheg "<query>" -cs "*" -ce "+15" -ud 

  note: see querying for more information on queries
""",
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument("queries", help="song queries (see querying)", nargs="+")
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        help="directory to output to, formattable (see formatting)",
        default="",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help=f"output file name format, formattable (see formatting)",
        default=OUT,
    )
    parser.add_argument(
        "-tf",
        "--timestamp-format",
        type=str,
        help="timestamp format, formattable (see formatting)",
        default=TIMESTAMP_FORMAT,
    )
    parser.add_argument(
        "-e",
        "--ext",
        type=str,
        help=f'file extension, defaults to "mp4"',
        default="mp4",
    )
    parser.add_argument("-sda", "--sdargs", help="args to pass to spotdl", default="")
    parser.add_argument(
        "-ffa",
        "--ffargs",
        help="args to pass to ffmpeg for clip creation",
        default=FFARGS,
    )
    parser.add_argument(
        "-cs",
        "--clip-start",
        help="specify clip start (default 0)",
        dest="clip_start",
        type=str,
        default=CLIP_START,
    )
    parser.add_argument(
        "-ce",
        "--clip-end",
        help="specify clip end (default +15)",
        dest="clip_end",
        type=str,
        default=CLIP_END,
    )
    parser.add_argument(
        "-i", "--image", help="specify custom image", type=Path, default=None
    )
    parser.add_argument(
        "-ud",
        "--use-defaults",
        help="use --clip-start as clip start and --clip-length as clip end",
        dest="use_defaults",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="say yes to every y/n prompt",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    # validate clip start/end
    start_timestamp = check_timestamp(0, args.clip_start)
    end_timestamp = check_timestamp(1, args.clip_end)

    if start_timestamp is None:
        console.print(f"{premsg_error} invalid clip start (format: \[hh:mm:]ss)")
        exit(1)

    if end_timestamp is None:
        console.print(
            f"{premsg_error} invalid clip end (format: \[hh:mm:]ss), "
            'prefix with "+" for relative timestamp'
        )
        exit(1)

    # validate formattables to make sure they dont contain illegal placeholders
    spotdl_replaceables = (
        "{artist}",
        "{artists}",
        "{title}",
        "{album}",
        "{playlist}",
    )
    for placeholder in spotdl_replaceables:
        if placeholder in args.timestamp_format:
            console.print(
                f"{premsg_error} specified timestamp format string contains illegal "
                f"placeholder ({placeholder})"
            )
            exit(1)

    pymtheg_replaceables = ("{cs}", "{css}", "{ce}", "{ces}", "{cer}")
    for placeholder in pymtheg_replaceables:
        if placeholder in str(args.dir):
            console.print(
                f"{premsg_error} specified dir format string contains illegal "
                f"placeholder ({placeholder})"
            )
            exit(1)

        if placeholder in str(args.out):
            console.print(
                f"{premsg_error} specified out format string contains illegal "
                f"placeholders ({placeholder})"
            )
            exit(1)

    bev = Behaviour(
        queries=args.queries,
        dir=Path(args.dir),
        out=args.out,
        timestamp_format=args.timestamp_format,
        ext=args.ext,
        sdargs=args.sdargs.split(),
        ffargs=args.ffargs.split(),
        clip_start=start_timestamp,
        clip_end=end_timestamp,
        image=args.image,
        use_defaults=args.use_defaults,
        yes=args.yes,
    )

    if not bev.dir.exists():
        console.print(f"{premsg_error} output directory is non-existent")
        exit(1)

    if not bev.dir.is_dir():
        console.print(f"{premsg_error} output directory is not a directory")
        exit(1)

    if bev.image is not None and not bev.image.exists():
        console.print(f"{premsg_error} specified image is non-existent")
        exit(1)

    return bev


if __name__ == "__main__":
    main()
