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
from datetime import datetime
from base64 import b85decode
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
    random: bool = False
        is timestamp random
    relative: bool = False
        is timestamp relative
    """

    type: Union[Literal[0], Literal[1]]
    ss: int
    random: bool = False
    relative: bool = False

    def __str__(self) -> str:
        return "*" if self.random else (("+" if self.relative else "") + str(self.ss))


class Behaviour(NamedTuple):
    """typed command line argument tuple"""

    song_queries: List[str]
    song_paths: List[Path]
    dir: Path
    out: str
    save_music: bool
    save_music_dir: Path
    no_timestamp: bool
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
        stdout: str = ""
        stderr: str = ""
        if len(bev.song_queries) > 0:
            with console.status(f"[dim]downloading songs...[/]", spinner="arc"):
                spotdl_proc = invocate(
                    console=console,
                    name="spotdl",
                    args=bev.song_queries
                    + ["--path-template", f"{bev.out}.{{ext}}"]
                    + bev.sdargs,
                    cwd=tmpdir,
                    errcode=2,
                    capture_output=True,
                )
                stdout = spotdl_proc.stdout
                stderr = spotdl_proc.stderr

        # process songs
        processed = 0

        for song in tmpdir.rglob("*"):
            # ensure that file was export of spotDL (list from spotdl -h)
            if song.suffix not in [".m4a", ".ogg", ".flac", ".mp3", ".wav", ".opus"]:
                continue

            if pymtheg(song, bev=bev, opdir=tmpdir, pp=processed, console=console):
                processed += 1

        for song in bev.song_paths:
            if pymtheg(song, bev=bev, opdir=tmpdir, pp=processed, console=console):
                processed += 1

    if processed > 0:
        console.print(
            f"\n{premsg_info} all operations successful. have a great {part_of_day()}."
        )

    else:
        if stdout != "":
            console.print(f"\n{premsg_error} invocation stdout:\n{stdout}")
        if stderr != "":
            console.print(f"\n{premsg_error} invocation stderr:\n{stderr}")

        console.print(
            f"{premsg_error} invalid link/query, nothing to do. (see above for more information)"
        )
        exit(1)


def pymtheg(
    song_path: Path, bev: Behaviour, opdir: Path, pp: int, console: Console
) -> bool:
    """
    where the magic happens

    song_path: Path
        path to song
    bev: Behaviour
        behaviour object
    opdir: Path
        an operation directory, usually a tmpdir
    pp: int
        number of already processed songs
    console: rich.console.Console
        rich console object used for printing
    """
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
        song_duration: int = int(loads(proc.stdout)["format"]["duration"].split(".")[0])

    if pp == 0:
        # print timestamp format/using default message on first song
        if bev.use_defaults:
            console.print(
                f'{premsg_info} using defaults, clip start is "{bev.clip_start}"'
                f' and clip end is "{bev.clip_end}"\n'
            )

        else:
            console.print(f"{premsg_info} enter timestamps in format \[hh:mm:]ss")
            console.print('               timestamp can be "*" for random')
            console.print('               end timestamp can be relative, prefix with "+"')
            console.print(
                f"               press enter to use given defaults "
                f'("{bev.clip_start}", "{bev.clip_end}")\n'
            )

    console.print(
        "- [bold]{name}[/]{duration}".format(
            name=song_path.stem,
            duration=f" ({to_timestamp(song_duration)})" if not bev.use_defaults else "",
        )
    )

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
    song_clip_path = opdir.joinpath(f"{song_path.stem}_clip.mp3").absolute()
    song_cover_path = opdir.joinpath(f"{song_path.stem}_cover.png").absolute()
    video_clip_path = opdir.joinpath(f"{song_path.stem}_clip.mp4").absolute()

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
        return False

    # construct and confirm output path
    out_path: Path = bev.dir.joinpath(
        "{name}{timestamp}.{ext}".format(
            name=song_path.stem,
            timestamp=tf_format(
                string=bev.timestamp_format,
                clip_start=start_timestamp,
                clip_end=end_timestamp,
            )
            if not bev.no_timestamp
            else "",
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
            return False

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
            cwd=opdir,
            errcode=3,
            capture_output=True,
        )

    # get album art if needed
    if bev.image is None:  # no custom image was specified
        with console.status(f"[dim]{info_status}get album art[/]", spinner="arc"):
            try:
                invocate(
                    console=console,
                    name="ffmpeg",
                    args=[
                        "-i",
                        song_path,
                        "-an",
                        song_cover_path,
                    ],
                    cwd=opdir,
                    errcode=3,
                    capture_output=True,
                    raise_illreturn=True,
                )

            except ChildProcessError:
                # file has no cover image, so use a placeholder
                with open(song_cover_path, "wb") as cv:
                    cv.write(b85decode(COVER_IMAGE_DATA.replace(b"\n", b"")))

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

    return True


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
        ts_start = randint(0, duration - 1)
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
    raise_illreturn: bool = False,
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
    raise_illreturn: bool = False
        raises a ChildProcessError if the process returns non-zero
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
            if raise_illreturn:
                raise ChildProcessError(proc.returncode)
            if capture_output:
                if proc.stdout != "":
                    console.print(f"\n{premsg_error} invocation stdout:\n{proc.stdout}")
                if proc.stderr != "":
                    console.print(f"\n{premsg_error} invocation stderr:\n{proc.stderr}")

            console.print(
                f"\n{premsg_error} error during invocation of "
                f'"{" ".join([str(p) for p in invocation])}", returned non-zero exit '
                f"code {proc.returncode}, see above for details"
            )
            exit(proc.returncode)

    except FileNotFoundError as err:
        console.print(
            f'\n[bold red]invocation:[/] "{" ".join([str(p) for p in invocation])}"'
        )
        console.print_exception()
        console.print(f"\n{premsg_error} could not invocate {name}, see details")
        exit(errcode)

    except ChildProcessError as err:
        raise err

    except Exception as err:
        console.print(
            f'\n[bold red]invocation:[/] "{" ".join([str(p) for p in invocation])}"'
        )
        console.print_exception()
        console.print(
            f"\n{premsg_error} unknown error during invocation of {name}, see details"
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
  queries must be any one of the following:
    1. text
      "<query>"
      e.g. "thundercat - them changes"
    2. spotify track/album url
      "<url>"
      e.g. "https://open.spotify.com/track/..."
    3. youtube source + spotify metadata
      "<youtube url>|<spotify url>"
      e.g. "https://youtube.com/watch?v=...|https://open.spotify.com/track/..."
    4. a path
      "<path>"
      e.g. "06 VERTIGO.flac"

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
           the first shown unit where they _may_ have up to two characters.
           hours can be represented by any number of characters.
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

    cargs = parser.add_argument_group("clip options")
    oargs = parser.add_argument_group("output options")
    targs = parser.add_argument_group("tool options")
    pargs = parser.add_argument_group("pymtheg options")

    cargs.add_argument(
        "-cs",
        "--clip-start",
        help="specify clip start (default 0)",
        type=str,
        default=CLIP_START,
    )
    cargs.add_argument(
        "-ce",
        "--clip-end",
        help="specify clip end (default +15)",
        type=str,
        default=CLIP_END,
    )
    cargs.add_argument(
        "-i", "--image", help="specify custom image", type=Path, default=None
    )

    oargs.add_argument(
        "-d",
        "--dir",
        type=Path,
        help="directory to output to, formattable (see formatting)",
        default="",
    )
    oargs.add_argument(
        "-o",
        "--out",
        type=Path,
        help=f"output file name format, formattable (see formatting)",
        default=OUT,
    )
    oargs.add_argument(
        "-sm",
        "--save-music",
        help="save downloaded music",
        action="store_true",
        default=False,
    )
    oargs.add_argument(
        "-smd",
        "--save-music-dir",
        type=Path,
        help=f"directory for downloaded music, defaults to -d/--dir",
        default="",
    )
    oargs.add_argument(
        "-nt",
        "--no-timestamp",
        help="switch to exclude timestamps from output clip paths",
        action="store_true",
        default=False,
    )
    oargs.add_argument(
        "-tf",
        "--timestamp-format",
        type=str,
        help="timestamp format, formattable (see formatting)",
        default=TIMESTAMP_FORMAT,
    )
    oargs.add_argument(
        "-e",
        "--ext",
        type=str,
        help=f'file extension, defaults to "mp4"',
        default="mp4",
    )

    targs.add_argument("-sda", "--sdargs", help="args to pass to spotdl", default="")
    targs.add_argument(
        "-ffa",
        "--ffargs",
        help="args to pass to ffmpeg for clip creation",
        default=FFARGS,
    )

    pargs.add_argument(
        "-ud",
        "--use-defaults",
        help="use --clip-start as clip start and --clip-length as clip end",
        action="store_true",
        default=False,
    )
    pargs.add_argument(
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

    song_queries: List[str] = []
    song_paths: List[Path] = []

    for query in args.queries:
        if Path(query).exists():
            song_paths.append(Path(query))
        else:
            song_queries.append(query)

    bev = Behaviour(
        song_queries=song_queries,
        song_paths=song_paths,
        dir=args.dir,
        out=args.out,
        save_music=args.save_music,
        save_music_dir=args.dir
        if args.save_music_dir == Path("")
        else args.save_music_dir,
        no_timestamp=args.no_timestamp,
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


# before you start panicking, this is simply a base85 encoded image file used when custom
# files are specified as queries but they do not have album covers
COVER_IMAGE_DATA = b"""
iBL{Q4GJ0x0000DNk~Le0006U0006U2nGNE0KNWqd;kCd32;bRa{vGU000000RV(~7jpmr3QS2vK~#9!?cL8Sd}|!Q
aX-ed!LYP2r4&0QC3gN7Nq)qVjjW{D*(v{ng-FfLQdUxy3Slij2Jw7*d^flIy~db($GJJLSDlT;nR=%5?#y$ZPfY*-
sInSM000OM06=g600<5MKyUy6f&&0RZ~y>;0{}p9004pm01zAi0D=Pm5F7x2-~a#+8~}je000mi0D#~C00ajBfZzZC
1P1^hH~;_y2LK>A000CB03bL30KowOAUFU3!2tjW4gdhb0RRXN006-O00<5MKyUy62o3;1Z~y>;0{}p9004pm06=g6
0D=Pm5F7vif&%~$8~}je000mi0D#~C01zAifZzZC1P1_s-~a#w2LK>A000CB03bL300ajBAUFU3!2tjuH~;{_0RRXN
006-O00<5M0KowO2o3;1Z~y=Z4gf%K004pm06=g60D=PmKyUy6f&%~$8~^}<0{{>l0D#~C01zAifZzZC5F7x2-~a#w
2LOQJ000CB03bL300ajBAUFU31P1^hH~;{_0RSL4006-O00<5M0KowO2o3-M!2tjW4gf%K000OM06=g60D=PmKyUy6
f&&0RZ~y>;0{{>l004pm01zAifZzZC5F7x2-~a#+8~}je000CB0D#~C00ajBAUFU31P1^hH~;_y2LK>A006-O03bL3
0KowO2o3-M!2tjW4gdhb0RRXN06=g600<5MKyUy62o3;1Z~y>;0{}p9004pm01zAi0D=Pm5F7vif&%~$8~}je000mi
0D#~C00ajBfZzZC1P1_s-~a#w2LK>A000CB03bL30KowOAUFU3!2tjuH~;{_0RRXN006-O00<5MKyUy62o3;1Z~y=Z
4gf%K004pm06=g60D=Pm5F7vif&%~$8~^}<0{{>l0D#~C01zAifZzZC1P1_s-~a#w2LOQJ000CB03bL300ajBAUFU3
!2tjuH~;{_0RSL4006-O00<5M0KowO2o3;1Z~y=Z4gf%K000OM06=g60D=PmKyUy6f&%~$8~^}<0{{>l004pm01zAi
fZzZC5F7x2-~a#w2LOQJ000CB0D#~C00ajBAUFU31P1^hH~;{_0RSL4006-O03bL30KowO2o3-M!2tjW4gf%K000OM
06=g600<5MKyUy6f&&0RZ~y>;1Nce*IBIIDdI5q1KyUzp1E{{*+FHQ@2o6AS0D=P$9D)M`2Y}!J1P73?y1F{S0SFF2
Z~%e>5FCO71P6fN00ak+u=@IX!2t*kKyUzp0}vd70|W<v-~a>%kg!Z9BRBxT0SFF2Z~#9%H~<6(AUFWQ0sQ|pG&Bef
KyUzp0}vd5-~a>%fZzZG2avGF#zw&b2o6AS0D=P$9Dv{e5FCKu00ajhIDnt7si{eD0D=P$9Dv{e1P35E00ajhIDmvT
H#Z9oKyUzp0}vd5-~a>%fZzZG2avFqmKMPQ2o6AS0D=P$9Dv{e5FCKu01}qXW(5ZzIDqmzKR<^;p%7+gXT#XoSm^8P
3%Oh_)YsRCo}QjCJUkrc=jX%r_I4;1i-H3X96<SQZf?TN%*=aSlnRHxUY(ttVQy|NTwPrW4nS}KAB#^ZmY0`9TU%S%
q4D=Cp21O9S0^|C!2$f~`uaMIj*eCw8eh2p1P7$h@$qr!?(Y7U*bp3m;DD4q*~sVf-xeE!0}vdLGI7tw$jHdI#)jYk
1P7$d($dnm$A;hl1P7!@{3)fiwY983i05ytudj!blap|JdmHZV?!xKmY1r7<2m=EHf&&m7z(1Rsn));hGMP+RTU!e+
FE1b7=k@h9Y;JCTI+9*+0D=Qj=IQAvbaZr-jDmQY=+4eg+4np+I4C<h00al5!2bUJr%|xFy87k&Zf$J|4nS}KzfDh1
mkfg5-rn~)Dqr>X_7;YQh6D#7IDqgzh^<r*tgNh5eDAoQLvR3s0|@>7{Uw9o@bIwWd!L=12@XJT03o!ux0eipI4!nP
@r@S4+W^4<BpMv?vjGGLq(G8Csl-FX00al5K$4qA<7Wd14oHC{UyF?=oB{|ANP#2|{@UBy^92Bc1JWR=qs`-n(PFXa
3jhQMq(u_L+a@L^EIc4MAWgn|JbgBs4VRaf79J2BkTy$8OJ$Fg|F_rT;-Uoy1P7#1+)ptwGE()}h;ObuJUm!%KyW}>
#h+I4`Fz!4qpPbcTwGjOXh3j4+8rMshwkp~s>H_8(UAoP1PAb2e9|#GI{Kf*#^B(fCmVp^0R9yBbSy6~hqku1ibEs5
9=oux5bp2qEhr#3fRDv#u`@F>A(zXQ9UAc!+wt-7aDIMn0Rh1QlrPRxDHIA}c6RoC=vq9FBSuJ!i#Ts3{%vw{GVJc|
hR4T83kC=d06=g60D=PmKyUy6f&&0RZ~y>;0{{>l004pm01zAifZzZC5F7x2-~a#+8~}je000CB0D#~C00ajBAUFU3
1P1^hH~;_y2LK>A006-O03bL30KowO2o6gC00<5MKyUy62o3;1Z~y>;0{}p9004pm06=g60D=Pm5F7vif&%~$8~}je
000mi0D#~C01zAifZzZC1P1_s-~a#w2LK>A000CB03bL300ajBAUFU3!2tjuH~;{_0RRXN006-O00<5M0KowO2o3;1
Z~y=Z4gf%K004pm06=g60D=PmKyUy6f&%~$8~^}<0{{>l0D#~C01zAifZzZC5F7x2-~a#w2LOQJ000CB03bL300ajB
AUFU31P1^hH~;{_0RSL4006-O00<5M0KowO2o3-M!2tjW4gf%K000OM06=g60D=PmKyUy6f&&0RZ~y>;0{{>l004pm
01zAifZzZC5F7x2-~a#+8~}je000CB0D#~C00ajBAUFU31P1^hH~;_y2LK>A006-O03bL30KowO2o3-M!2tjW4gdhb
0RRXN06=g600<5MKyUy6f&&0RZ~y>;0{}p9004pm01zAi0D=Pm5F7x2-~a#+8~}je000mi0D#~C00ajBfZzZC1P1^h
H~;_y2LK>A000CB03bL30KowOAUFU3!2tjW4gdhb0RRXN006-O00<5MKyUy62o3;1Z~y=Z4gf%K004pm06=g60D=Pm
5F7vif&%~$8~^}<0{{>l0D#~C01zAifZzZC1P1_s-~a#w2LOQJ000CB03bL300ajBAUFU3!2tjuH~;{_0RSL4006-O
00<5M0KowO2o3;1Z~y=Z4gf%K000OM06=g60D=PmKyUy6f&%~$8~^}<0{{>l004pm01zAifZzZC5F7x2-~a#w2LOQJ
000CB0D#~C00ajBAUFU31P1^hH~;{_0RSL4006-O03bL30KowO2o3-M!2tjW4gf%K000OM06=g600<5MKyUy6f&&0R
Z~y>;0{{>l004pm01zAi0D=Pm5F7x2-~a%qz%RDyFKU20J8A#`002ovPDHLkV1f"""


if __name__ == "__main__":
    main()
