"""
pymtheg: A Python script to share songs from Spotify/YouTube as a 15 second clip
-------

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
"""

from json import loads
from typing import Iterable, List, NamedTuple, Optional, Type, Union

from tempfile import TemporaryDirectory
from argparse import ArgumentParser
from traceback import print_tb
from datetime import datetime
from pathlib import Path
import subprocess


QUERY_CLIP_START = "  -   clip end: "
QUERY_CLIP_END = "  - clip start: "
QUERY_CLIP_STATUS = "  -     status: "

MSG_INFO = ""
MSG_DEBUG = ""
MSG_ERROR = ""

FFARGS: str = (
    "-hide_banner -loglevel error -loop 1 -c:a aac -vcodec libx264 -pix_fmt yuv420p "
    "-preset ultrafast -tune stillimage -shortest"
)


class Behaviour(NamedTuple):
    """
    typed command line argument tuple
    """

    query: str
    dir: Path
    out: Optional[Path]
    sdargs: List[str]
    ffargs: List[str]
    clip_length: int
    use_defaults: bool


def main() -> None:
    """
    pymtheg entry point
    """
    bev = get_args()

    # make tempdir
    with TemporaryDirectory() as _tmpdir:
        # print(f"pymtheg: debug: {_tmpdir}")
        tmpdir = Path(_tmpdir)

        # download songs
        invocate(name="spotdl", args=[bev.query] + bev.sdargs, cwd=tmpdir, errcode=2)

        # process songs
        if bev.use_defaults:
            print(
                "\npymtheg: info: using defaults, clip start will be 0 and clip end will"
                f" be {bev.clip_length}\n"
            )

        else:
            print("\npymtheg: info: enter timestamps in format [hh:mm:]ss")
            print("               end timestamp can be relative, prefix with '+'")
            print("               press enter to use given defaults\n")

        for song_path in tmpdir.rglob("*.*"):
            # ensure that file was export of spotDL (list from spotdl -h)
            if song_path.suffix not in [".m4a", ".ogg", ".flac", ".mp3", ".wav", ".opus"]:
                continue

            print(f"- {song_path.stem}")

            _msg = f"{QUERY_CLIP_STATUS}probe song duration"
            print(_msg, end="\r")

            # duration retrieval
            proc = invocate(
                "ffprobe",
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

            print(" " * len(_msg), end="\r")

            # get timestamps
            start_timestamp = 0
            end_timestamp: int = start_timestamp + bev.clip_length

            if not bev.use_defaults:
                # starting timestamp
                while True:
                    response = input(f"{QUERY_CLIP_START}0\r{QUERY_CLIP_START}")

                    if response != "":
                        _start_timestamp = parse_timestamp(response)

                        if _start_timestamp is None:
                            # invalid format
                            print(
                                (" " * len(QUERY_CLIP_START)) + ("^" * len(response)),
                                "invalid timestamp",
                            )

                        elif _start_timestamp >= song_duration:
                            # invalid, timestamp >= song duration
                            print(
                                (" " * len(QUERY_CLIP_START)) + ("^" * len(response)),
                                "timestamp exceeds song duration",
                            )

                        else:
                            # valid, continue
                            start_timestamp = _start_timestamp
                            break

                    elif response == "":
                        break

                # ending timestamp
                while True:
                    response = input(
                        f"{QUERY_CLIP_END}+{bev.clip_length}\r{QUERY_CLIP_END}"
                    )
                    if response != "":
                        _end_timestamp = parse_timestamp(
                            response, relative_to=start_timestamp
                        )

                        if _end_timestamp is None:
                            # reprompt if invalid
                            print(
                                (" " * len(QUERY_CLIP_END)) + ("^" * len(response)),
                                "invalid timestamp",
                            )

                        else:
                            end_timestamp = _end_timestamp
                            break

                    elif response == "":
                        break

            # construct paths
            song_path = song_path.absolute()
            song_clip_path = tmpdir.joinpath(f"{song_path.stem}_clip.mp3").absolute()
            song_cover_path = tmpdir.joinpath(f"{song_path.stem}_cover.png").absolute()
            out_path: Path = bev.dir.joinpath(f"{song_path.stem}.mp4").absolute()

            if bev.out is not None:
                out_path = bev.out

            # clip audio
            _msg = f"{QUERY_CLIP_STATUS}clip audio"
            print(_msg, end="\r")

            invocate(
                "ffmpeg",
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

            print(" " * len(_msg), end="\r")

            # get album art
            _msg = f"{QUERY_CLIP_STATUS}getting album art"
            print(_msg, end="\r")

            invocate(
                "ffmpeg",
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

            print(" " * len(_msg), end="\r")

            # create clip
            print(f"{QUERY_CLIP_STATUS}creating clip")  # no \r because ffmpeg output

            invocate(
                "ffmpeg",
                args=["-i", song_cover_path, "-i", song_clip_path, *bev.ffargs, out_path],
                errcode=3,
            )

    print(f"\npymtheg: info: all operations successful. have a great {part_of_day()}.")


def part_of_day():
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


def parse_timestamp(ts: str, relative_to: Optional[int] = 0) -> Optional[int]:
    """
    parse user-submitted timestamp

    ts: str
        timestamp following [hh:mm:]ss format (e.g. 2:49, 5:18:18)
    """
    timestamp = 0

    if ts.startswith("+") and relative_to is not None:
        ts = ts[1:]
        timestamp += relative_to

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

        return timestamp + total_ss

    else:
        return None


def invocate(
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
                    print(f"\npymtheg: error: invocation stdout:\n{proc.stdout}")
                if proc.stderr != "":
                    print(f"\npymtheg: error: invocation stderr:\n{proc.stderr}")

            print(
                "\npymtheg: error: error during invocation of "
                f"'{' '.join([str(p) for p in invocation])}', returned non-zero exit "
                f"code {proc.returncode}, see above for details"
            )
            exit(proc.returncode)

    except FileNotFoundError as err:
        print_tb(err.__traceback__)
        print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"pymtheg: error: could not invocate {name}, see traceback"
        )
        exit(errcode)

    except Exception as err:
        print_tb(err.__traceback__)
        print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"pymtheg: error: unknown error during invocation of {name}, see traceback"
        )
        exit(errcode)

    else:
        return proc


def get_args() -> Behaviour:
    """
    parse and validate arguments
    """
    # parse
    parser = ArgumentParser(
        prog="pymtheg",
        description=(
            "a python script to share songs from Spotify/YouTube as a 15 second clip"
        ),
        epilog=f"ffargs default: '{FFARGS}'",
    )

    parser.add_argument("query", help="song/link from spotify/youtube")
    parser.add_argument(
        "-d", "--dir", type=Path, help="directory to output to", default=Path.cwd()
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help="output file path, overrides directory arg",
        default=None,
    )
    parser.add_argument("-sda", "--sdargs", help="args to pass to spotdl", default="")
    parser.add_argument(
        "-ffa",
        "--ffargs",
        help="args to pass to ffmpeg for clip creation",
        default=FFARGS,
    )
    parser.add_argument(
        "-cl",
        "--clip-length",
        help="length of output clip in seconds (default 15)",
        dest="clip_length",
        type=int,
        default=15,
    )
    parser.add_argument(
        "-ud",
        "--use-defaults",
        help="use 0 as clip start and --clip-length as clip end",
        dest="use_defaults",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    bev = Behaviour(
        query=args.query,
        dir=args.dir,
        out=args.out,
        sdargs=args.sdargs.split(),
        ffargs=args.ffargs.split(),
        clip_length=args.clip_length,
        use_defaults=args.use_defaults,
    )

    # validate:
    if bev.out is not None:
        if bev.out.is_dir():
            print("pymtheg: error: output file is a directory")
            exit(1)

        if bev.out.exists():
            override_response = input(f"pymtheg: info: {bev.out} exists, override? (y/n)")
            if override_response.lower() != "y":
                exit(1)

    if not bev.dir.exists():
        print("pymtheg: error: output directory is non-existent")
        exit(1)

    if not bev.dir.is_dir():
        print("pymtheg: error: output directory is not a directory")
        exit(1)

    return bev


if __name__ == "__main__":
    main()
