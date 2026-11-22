# What to test — in priority order

(As posted on Mimir's Memory Hub Discussion #23, 2026-11-22.)

1. **Continuity, qualitatively.** After a restart, does the model wake up
   *inside* the thread, or does it feel like it's reading someone else's
   notes back cold? That distinction is the whole experiment. Your read
   matters more than any number here.
2. **Trail packet quality.** Each pulse, the walk produces a small packet
   that steers the next response. Does it steer like the same mind
   continuing, or like a summary being handed over?
3. **Cost on consumer hardware.** Tokens per pulse and per hour at your
   model size, and wall-clock per pulse on the 5060 Ti. Sustained
   pulses/hour is the benchmark that matters.
4. **Settling behavior.** Over a few days, does the web settle into a
   resting state, or does it thrash? The live one rests. Interested
   whether a fresh seed does too.
5. **Breakage.** Especially state save/restore: kill it mid-pulse and see
   whether it holds its place on restart.

Results in Discussion #23 are perfect.
