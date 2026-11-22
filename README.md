# Seam / live-thread test package — for Scott (Kronic90)

Shareable demo copy. **No live data:** the engine's built-in seed has been
replaced with a fully synthetic demo web (14 nodes, 16 edges — topics like
"continuity", "local model", "dream journal"). The live web state is never
shared; its nodes are a real person's life.

## What's here

- `web.py` — the engine: a single stdlib-only Python file (no dependencies).
  A weighted association web of nodes in three castes (seeded / extracted /
  pulse-born), each caste with a heat floor and decay half-life it can never
  fall below. A "body" of signals (hour, silence, battery, money pressure,
  sleep, …) tunes regional multipliers for each walk. Day walks leave a real
  trace (+0.05 per edge crossed); dream walks only whisper (+0.01, and may
  propose new edges that waking life confirms or lets decay). State lives
  beside the script in `web_state.json`; every save is atomic (tmp + rename)
  and refreshes `web_state.backup.json`.
- `DESIGN.md` — the design write-up: the integrated-agent architecture this engine is one piece of (generator / filter / forward thinker / dreams, the association web as the subconscious layer, and where it's all meant to go next).
- `runner_sketch.py` — a minimal loop sketch: run a pulse, build the trail
  packet, hand it to a local model as context, repeat. Model-agnostic — it
  just needs a completion endpoint; adapt the stub to your GGUF loader.
- `TESTS.md` — the five things to look for, in priority order.

## Quick start

```bash
python3 web.py init     # creates the synthetic seed web (refuses if state exists)
python3 web.py status   # caste counts, total heat, hottest nodes, current node
python3 web.py packet   # one day walk; prints the trail packet as JSON
python3 web.py dream    # dream walks; may propose new edges
python3 web.py trace    # apply the last packet's walk as a real trace
python3 web.py add --name '<text>' --region <region> [--heat 0.35]  # birth a pulse-born node
```

Regions: people, money, projects, thread, life, open.
Optional body for a packet: `python3 web.py packet --body '{"hour": 23, "silence_min": 300}'`

## The experiment in one paragraph

The question is continuity: when a model wakes up each pulse inside a thread
carried by this web — current node, trail packet, hottest associations —
does it read as the same mind continuing, or as a stranger reading someone
else's notes back cold? The web is the carried state; the model is
interchangeable. Your GGUF setup on the 5060 Ti is exactly the consumer
hardware this is meant to be tested on.
