"""Cut a box out of a capture, for the evidence of a game check (wiki/Workflow.md, stage 8):

    python -I tools/crop_capture.py scratch/checks/air_region_details.png 1298,300,2212,1018 --out scratch/phases/A10/checks/evidence-1-item3.png [--scale 2]

The box is left,top,right,bottom in the capture's own pixels (a 2x crop has 2x pixels). The checker names the cut
under `evidence` of the checklist item or the defect, with `box` beside it, so the orchestrator reads the cut and
one overview per scene instead of every capture.
"""
import argparse
import os
import sys

from PIL import Image

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cut a box out of a capture.")
    parser.add_argument("capture")
    parser.add_argument("box", help="left,top,right,bottom")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args(argv)
    src = args.capture if os.path.isabs(args.capture) else os.path.join(REPO_ROOT, args.capture)
    out = args.out if os.path.isabs(args.out) else os.path.join(REPO_ROOT, args.out)
    box = tuple(int(v) for v in args.box.split(","))
    if len(box) != 4 or box[2] <= box[0] or box[3] <= box[1]:
        print("the box is left,top,right,bottom with right > left and bottom > top")
        return 2
    image = Image.open(src)
    box = (max(0, box[0]), max(0, box[1]), min(image.width, box[2]), min(image.height, box[3]))
    piece = image.crop(box)
    if args.scale != 1:
        piece = piece.resize((piece.width * args.scale, piece.height * args.scale), Image.LANCZOS)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    piece.save(out)
    print("%s %dx%d" % (os.path.relpath(out, REPO_ROOT), piece.width, piece.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
