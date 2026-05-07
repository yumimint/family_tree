import argparse
import io
import pathlib
import sys

import pyperclip  # type: ignore

from family_tree import Family, make_pdf


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Generates a family tree graph from a simple text file"
    )
    parser.add_argument(
        "input",
        default=None,
        nargs="?",
        help="the formatted text file representing the family",
    )
    parser.add_argument(
        "-c",
        nargs="?",
        const="FamilyTree",
        default=None,
        metavar="OUTNAME",
        help="read fron clipboard",
    )
    parser.add_argument("-v", action="store_true")
    args = parser.parse_args()

    fam = Family()

    if args.input is not None:
        input = pathlib.Path(args.input)
        with input.open("r", encoding="utf-8") as f:
            fam.populate(f.readlines()[1:])
    elif args.c is not None:
        lines = pyperclip.paste().split("\n")
        fam.populate(lines[1:])

    fam.postprocess()
    make_pdf(fam, args.c, view=args.v)


if __name__ == "__main__":
    main()
