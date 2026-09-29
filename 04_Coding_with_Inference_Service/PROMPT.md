# Crash Course: Monte Carlo Pi With a Coding Agent

Work with a coding agent to estimate pi by random sampling, check that the answer is
right, and make a figure of the result. `solution.py` is one finished version you can
compare against. Don't show it to the agent.

## Before you start

```bash
cd Service_Enabled_Science
./setup.sh                    # skip if you already ran it
source .venv/bin/activate     # numpy + matplotlib are now on PATH
mkdir -p ~/pi-demo && cd ~/pi-demo
git init                      # your undo button
opencode                      # choose Inkling on Minerva

# If opencode is not in PATH:
~/.opencode/bin/opencode
```

Working in a new directory keeps `solution.py` out of the agent's view.

## The prompt

Start in **Plan** mode (`Tab`). Paste the prompt, read the plan, then press `Tab`
again to switch to **Build** and tell it to go ahead.

```text
Write a single Python script, pi_mc.py, that estimates pi with Monte Carlo sampling
and makes a publication-quality figure of the result.

Environment:
- Use the `python` already on PATH. It is an activated virtualenv with numpy and
  matplotlib installed. Do not pip install anything or create a new environment.
- This is a headless terminal: save the figure with savefig. Never call plt.show().

The math:
- Draw N points uniformly in the unit square with numpy (np.random.default_rng(seed)),
  vectorized, with no Python loops over samples.
- p = fraction with x^2 + y^2 <= 1. Estimate pi_hat = 4p.
- Standard error: 4 * sqrt(p * (1 - p) / N).

Command line (argparse): --samples/-n (default 1_000_000), --seed (default 0),
--out (default pi_monte_carlo.png).

Print N, the estimate with its standard error, and how many standard errors it lies
from math.pi. Fail with an error if that is more than 3.

The figure (one PNG, about 13x6 inches, dpi 150, constrained layout):
1. Left panel: a scatter of the first 5,000 points, blue inside the circle and
   orange outside, with the quarter-circle arc drawn and equal aspect ratio.
2. Top right: the running estimate of pi versus number of samples, with a log
   x-axis, a shaded +/-2 sigma band, and a dashed line at the true pi.
3. Bottom right: |pi_hat - pi| versus N on log-log axes, with a dashed reference
   line sigma/sqrt(N), where sigma = 4*sqrt(pi/4 * (1 - pi/4)).
Compute running values with np.cumsum, then plot only about 2,000 points spaced
logarithmically, so plotting doesn't draw a million-point line.
Use a clean style: remove the top and right spines, use a light grid, and give each
panel a title and axis labels. Put a suptitle with the final estimate +/- its error.

When you are done, run `python pi_mc.py` and `python pi_mc.py -n 1000 --seed 3`,
show me the printed output, and fix any errors before you report back.
```

## Check the agent's work

1. **Run it yourself:** `python pi_mc.py`. With 10^6 samples the estimate should be
   within about 0.003 of 3.14159.
2. **Open the PNG.** The inside/outside boundary should follow the arc. The
   estimate should settle onto the dashed pi line. The error curve should slope
   downward at about the same angle as the dashed reference line.
3. **Read the diff.** Look for any `for` loop over samples, `plt.show()`, or a
   `pip install`.
4. **Commit** once it works: `git add -A && git commit -m "Monte Carlo pi"`.

## Follow-up prompts

Send these one at a time, and run the script after each one:

- `Add a --batches option that runs K independent seeds and reports the mean and
  spread of the estimates. Is the spread consistent with the standard error?`
- `Time the sampling for N = 10^5 .. 10^8 and add a note on how runtime scales.`
- `Write a pytest test that checks the estimate is within 4 standard errors of pi
  for three different seeds.`
- `Replace uniform sampling with a Sobol sequence (scipy.stats.qmc) and compare how
  fast the error falls.` The agent may need to install scipy for this, so decide
  whether to allow it.

## If it goes wrong

- **The code calls `plt.show()` or hangs:** tell the agent "headless: savefig only."
- **The code loops over samples in Python and is slow:** paste the runtime and ask
  it to vectorize with numpy.
- **It tries to `pip install`:** say no. Point it back to the Environment section.
- **It goes in circles:** use `/undo`, or start a new session with the prompt above.
  Don't pile on more corrections.
