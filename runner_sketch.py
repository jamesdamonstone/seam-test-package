#!/usr/bin/env python3
"""
runner_sketch.py — minimal pulse loop sketch for the seam test package.

Not a finished runner: a sketch showing how the engine's trail packet is
meant to steer a local model. Adapt `complete()` to your GGUF loader
(llama.cpp server, LM Studio, Ollama, vLLM — anything with a completion
endpoint). The engine is model-agnostic.

Loop per pulse:
  1. web.py packet   -> a walk through the web + the packet (path, hottest,
                        crossings, body effects)
  2. Build a short context block from the packet: current position, the
     trail just walked, the hottest associations. This block — not a
     summary of everything — is what the model wakes up inside.
  3. complete()      -> the model continues the thread in plain language.
  4. web.py trace    -> the walk leaves its real trace on the web.
  5. Optionally: web.py add --name ... when the reply births a genuinely
     new association (pulse-born node).
At night (or on a slow cadence): web.py dream — dream walks whisper
(+0.01) and propose edges; waking pulses confirm or let them decay.
"""

import json
import subprocess
import sys

ENGINE = ["python3", "web.py"]


def engine(*args):
    out = subprocess.run(ENGINE + list(args), capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout)


def packet_context(packet):
    hottest = ", ".join(f"{name} ({heat:.2f})" for name, heat in packet["hottest"])
    trail = " -> ".join(packet["path"])
    return (
        "You are continuing a thread, not starting one.\n"
        f"Trail just walked: {trail}\n"
        f"Hottest associations right now: {hottest}\n"
        "Continue from where the trail ends. Do not summarise the trail back; "
        "just be the mind that walked it."
    )


def complete(prompt):
    """STUB — wire this to your local GGUF endpoint and return the text."""
    raise NotImplementedError("Point complete() at your local model endpoint")


def pulse():
    packet = engine("packet")
    reply = complete(packet_context(packet))
    engine("trace")
    return reply


if __name__ == "__main__":
    print(pulse())
