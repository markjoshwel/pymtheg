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

from typing import Iterable, List, NamedTuple, Optional, Union

from tempfile import TemporaryDirectory
from argparse import ArgumentParser
from traceback import print_tb
from datetime import datetime
from pathlib import Path
import subprocess


class Behaviour(NamedTuple):
    """
    typed command line argument tuple
    """

    query: str
    dir: Optional[Path]
    out: Optional[Path]
    sdargs: str
    clip_length: int


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
        invocate(
            name="spotdl", args=[bev.query] + bev.sdargs.split(), cwd=tmpdir, errcode=2
        )

        # process songs
        print("\npymtheg: info: enter timestamps in format [hh:mm:]ss")
        print("               end timestamp can be relative, prefix with '+'")
        print("               press enter to use given defaults")

        for song_path in tmpdir.rglob("*.mp3"):
            print(f"  {song_path.stem}")

            # get starting timestamp
            start_timestamp = 0

            _query = "    clip start: "
            while True:
                response = input(f"{_query}0\r{_query}")

                if response != "":
                    _start_timestamp = parse_timestamp(response)

                    if _start_timestamp is None:
                        # reprompt if invalid
                        print(
                            (" " * len(_query)) + ("^" * len(response)),
                            "invalid timestamp",
                        )

                    else:
                        start_timestamp = _start_timestamp
                        break

                elif response == "":
                    break

            # get ending timestamp
            end_timestamp: int = start_timestamp + bev.clip_length

            _query = "      clip end: "
            while True:
                response = input(f"{_query}+{bev.clip_length}\r{_query}")
                if response != "":
                    _end_timestamp = parse_timestamp(
                        response, relative_to=start_timestamp
                    )

                    if _end_timestamp is None:
                        # reprompt if invalid
                        print(
                            (" " * len(_query)) + ("^" * len(response)),
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
            out_path: Path = Path(f"{song_path.stem}.mp4")

            if bev.out is not None:
                out_path = bev.out
            elif bev.dir is not None:
                out_path = bev.dir.joinpath(f"{song_path.stem}.mp4")

            # clip audio
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
            )

            # get album art
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
            )

            # make video
            invocate(
                "ffmpeg",
                args=[
                    "-loop",
                    "1",
                    "-i",
                    song_cover_path,
                    "-i",
                    song_clip_path,
                    "-c:a",
                    "aac",
                    "-vcodec",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-preset",
                    "ultrafast",
                    "-tune",
                    "stillimage",
                    "-shortest",
                    out_path,
                ],
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
) -> subprocess.CompletedProcess:
    """
    invocates command using subprocess.run

    name: str,
        name of program
    args: Iterable[Optional[Union[str, Path]]] = [],
        args of program, e.g. ["download", "-o=$HOME"]
    wd: Optional[Path] = None,
        working directory for process to be run
    errcode: int = -1,
        exit code for if the process returns non-zero
    """

    invocation: List[Union[str, Path]] = [name]

    for arg in args:
        if arg is not None:
            invocation.append(arg)

    try:
        print(
            f"pymtheg: info: invocating command '{' '.join([str(p) for p in invocation])}'\n"
        )
        return subprocess.run(invocation, cwd=cwd, universal_newlines=True, check=True)

    except FileNotFoundError as err:
        print_tb(err.__traceback__)
        print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"pymtheg: error: could not invocate {name}, see traceback"
        )
        exit(errcode)

    except subprocess.CalledProcessError as err:
        print_tb(err.__traceback__)
        print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"pymtheg: error: error during invocation of {name}, see traceback"
        )
        exit(errcode)

    except Exception as err:
        print_tb(err.__traceback__)
        print(
            f"{err.__class__.__name__}: {err}\n\n"
            f"pymtheg: error: unknown error during invocation of {name}, see traceback"
        )
        exit(errcode)


def get_args() -> Behaviour:
    """
    parse and validate arguments
    """
    # parse
    parser = ArgumentParser(
        prog="pymtheg",
        description="a python script to share songs from Spotify/YouTube as a 15 second clip",
    )

    parser.add_argument("query", help="song/link from spotify/youtube")
    parser.add_argument(
        "-d", "--dir", type=Path, help="directory to output to", default=None
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
        "-cl",
        "--clip-length",
        help="length of output clip in seconds (default 15)",
        dest="clip_length",
        type=int,
        default=15,
    )

    args = parser.parse_args()
    bev = Behaviour(
        query=args.query,
        dir=args.dir,
        out=args.out,
        sdargs=args.sdargs,
        clip_length=args.clip_length,
    )

    # validate
    if bev.out is not None and bev.out.exists():
        override_response = input(f"pymtheg: info: {bev.out} exists, override? (y/n)")
        if override_response.lower() != "y":
            exit(1)

    if bev.dir is not None:
        if not bev.dir.exists():
            print("pymtheg: error: output directory is non-existent")
            exit(1)

        if not bev.dir.is_dir():
            print("pymtheg: error: output directory is not a directory")
            exit(1)

    return bev


if __name__ == "__main__":
    main()
