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

from typing import Iterable, List, NamedTuple, Optional

from argparse import ArgumentParser, Namespace
from tempfile import TemporaryDirectory
from traceback import print_tb
from pathlib import Path
import subprocess


CMD_SPOTDL_DOWNLOAD = "spotdl {query} {sdargs} -of mp3"


class Behaviour(NamedTuple):
    query: str
    dir: Optional[Path]
    out: Optional[Path]
    sdargs: Optional[str]


def main() -> None:
    bev = get_args()

    with TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)
        invocate(name="spotdl", args=[bev.sdargs, bev.query], cwd=tmpdir, errcode=2)

        for song in tmpdir.rglob("*.mp3"):
            # TODO
            ...


def invocate(
    name: str,
    args: Iterable[Optional[str]] = [],
    cwd: Optional[Path] = None,
    errcode: int = -1,
) -> subprocess.CompletedProcess:
    invocation: List[str] = [name] + [arg for arg in args if arg is not None]

    try:
        print(f"pymtheg: info: invocating command '{' '.join(invocation)}'")
        return subprocess.run(
            invocation,
            cwd=cwd,
            shell=True,  # kowai
        )

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
    parser.add_argument("-sda", "--sdargs", help="args to pass to spotdl", default=None)

    args = parser.parse_args()
    bev = Behaviour(query=args.query, dir=args.dir, out=args.out, sdargs=args.sdargs)

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
