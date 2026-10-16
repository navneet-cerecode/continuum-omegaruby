"""Readable, labeled edit of actual recorded workflows; no fabricated UI/model output."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
work = ROOT / ".runtime/demo-edit"
work.mkdir(exist_ok=True)
font = "C\\:/Windows/Fonts/arial.ttf"


def run(args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        check=True,
        cwd=ROOT,
    )


def title(name, text, seconds):
    file = work / (name + ".txt")
    file.write_text(text, encoding="utf-8")
    relative = file.relative_to(ROOT).as_posix()
    output = work / (name + ".mp4")
    run(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=0x163f35:s=1440x1050:r=25",
            "-vf",
            f"drawtext=fontfile='{font}':textfile='{relative}':fontcolor=white:fontsize=40:x=90:y=(h-text_h)/2:line_spacing=22",
            "-t",
            str(seconds),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


def clip(name, input, factor, label):
    file = work / (name + ".txt")
    file.write_text(label, encoding="utf-8")
    relative = file.relative_to(ROOT).as_posix()
    output = work / (name + ".mp4")
    run(
        [
            "-i",
            str(ROOT / "artifacts" / input),
            "-vf",
            f"setpts={factor}*PTS,fps=25,drawbox=x=0:y=0:w=iw:h=54:color=0x163f35:t=fill,drawtext=fontfile='{font}':textfile='{relative}':fontcolor=white:fontsize=23:x=24:y=15",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


parts = [
    title(
        "intro",
        "CONTINUUM / OmegaRuby\nTrack 3 - Company Brain\n\nActual browser workflows, real FalkorDB\nFictional Northstar Systems data\nAI assistance: OpenAI Codex\nSilent recording; workflow sections slowed for readability",
        9,
    ),
    clip(
        "cycles",
        "CONTINUUM-two-cycle-demo.webm",
        6,
        "1 / Two real approval cycles and retained history - playback slowed 6x",
    ),
    clip(
        "accounts",
        "CONTINUUM-account-onboarding-demo.webm",
        5,
        "2 / Account roles, older records and reviewed source import - slowed 5x",
    ),
    clip(
        "agent",
        "CONTINUUM-live-agent-demo.webm",
        1.5,
        "3 / Genuine local Ollama llama3:latest + graph tools - slowed 1.5x",
    ),
    title(
        "limits",
        "Verified locally: 114 tests and five live model scenarios\n\nCurated synthetic relationships; human-mapped Markdown\nCitation coverage is checked; prose entailment is unverified\nAccount mode is optional; the original demo stays intact\nFresh remote Linux build, tests and container restart passed\nParticipant understanding and submission require human completion",
        10,
    ),
]
listing = work / "parts.txt"
listing.write_text(
    "".join("file '" + str(p).replace("\\", "/") + "'\n" for p in parts),
    encoding="utf-8",
)
output = ROOT / "artifacts/CONTINUUM-OmegaRuby-demo.mp4"
run(
    [
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output),
    ]
)
metadata = json.loads(
    subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,width,height",
            "-of",
            "json",
            str(output),
        ],
        text=True,
    )
)
report = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "file": output.name,
    "actual_recordings": True,
    "synthetic_data": True,
    "narration": False,
    "workflow_speed_factors": [6, 5, 1.5],
    "metadata": metadata,
    "uploaded": False,
    "note": "Labeled edit of recorded UI, not a fabricated model or participant presentation. Review before submission.",
}
(ROOT / "artifacts/release-video.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
