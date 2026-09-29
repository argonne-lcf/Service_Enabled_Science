"""Estimate pi by Monte Carlo sampling and plot how the estimate converges.

Throw N points uniformly into the unit square. The fraction p that lands
inside the quarter circle x^2 + y^2 <= 1 estimates its area, pi/4, so

    pi_hat = 4 p,    standard error = 4 sqrt(p (1 - p) / N).

The error shrinks like N^(-1/2): each extra digit of pi costs 100x more
samples. The figure shows the samples, the running estimate with its
confidence band, and the error on log-log axes against that N^(-1/2) law.

    python solution.py                   # 1,000,000 samples, seed 0
    python solution.py -n 10_000_000 --seed 42 --out pi.png
"""

import argparse
import math

import matplotlib.pyplot as plt
import numpy as np

INSIDE = "#2a78d6"
OUTSIDE = "#eb6834"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

MAX_SCATTER = 5_000  # more points than this is just a solid blob


def sample(n, rng):
    """Return the points and a boolean mask of which fall inside the circle."""
    xy = rng.random((n, 2))
    inside = np.einsum("ij,ij->i", xy, xy) <= 1.0
    return xy, inside


def running_estimate(inside):
    """Estimate and standard error of pi after each of the first k samples."""
    k = np.arange(1, inside.size + 1)
    p = np.cumsum(inside) / k
    return k, 4 * p, 4 * np.sqrt(p * (1 - p) / k)


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot(xy, inside, out):
    k, est, err = running_estimate(inside)
    n = inside.size

    # Sample the running curves on a log grid: a million-point line is slow
    # to draw and looks no different.
    idx = np.unique(np.geomspace(1, n, 2_000).astype(int)) - 1
    k, est, err = k[idx], est[idx], err[idx]

    fig = plt.figure(figsize=(13, 6.2), facecolor=SURFACE, layout="constrained")
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 1.35])
    ax_pts = fig.add_subplot(grid[:, 0])
    ax_est = fig.add_subplot(grid[0, 1])
    ax_err = fig.add_subplot(grid[1, 1], sharex=ax_est)
    for ax in (ax_pts, ax_est, ax_err):
        style_axes(ax)

    # Left: the dartboard.
    m = min(n, MAX_SCATTER)
    pts, hit = xy[:m], inside[:m]
    ax_pts.scatter(*pts[hit].T, s=6, color=INSIDE, linewidths=0, label="inside")
    ax_pts.scatter(*pts[~hit].T, s=6, color=OUTSIDE, linewidths=0, label="outside")
    theta = np.linspace(0, np.pi / 2, 200)
    ax_pts.plot(np.cos(theta), np.sin(theta), color=INK, linewidth=1.5)
    ax_pts.set(xlim=(0, 1), ylim=(0, 1), aspect="equal")
    ax_pts.set_xlabel("x", color=MUTED)
    ax_pts.set_ylabel("y", color=MUTED)
    ax_pts.set_title(
        f"First {m:,} of {n:,} samples", color=INK, loc="left", fontsize=11
    )
    ax_pts.legend(loc="lower left", frameon=True, facecolor=SURFACE,
                  edgecolor=GRID, framealpha=1, fontsize=9, markerscale=2)

    # Top right: the running estimate closing in on pi.
    ax_est.fill_between(k, est - 2 * err, est + 2 * err, color=INSIDE,
                        alpha=0.15, linewidth=0, label=r"$\pm 2\sigma$")
    ax_est.plot(k, est, color=INSIDE, linewidth=2, label=r"$\hat\pi$")
    ax_est.axhline(math.pi, color=INK, linewidth=1, linestyle="--",
                   label=r"$\pi$")
    ax_est.set_xscale("log")
    ax_est.set_ylim(math.pi - 0.5, math.pi + 0.5)
    ax_est.set_ylabel("estimate", color=MUTED)
    ax_est.set_title("Running estimate", color=INK, loc="left", fontsize=11)
    ax_est.legend(loc="upper right", frameon=False, fontsize=9, ncols=3)
    ax_est.tick_params(labelbottom=False)

    # Bottom right: the error follows the N^(-1/2) law.
    abs_err = np.abs(est - math.pi)
    ax_err.loglog(k, np.where(abs_err > 0, abs_err, np.nan), color=INSIDE,
                  linewidth=1.5, label=r"$|\hat\pi - \pi|$")
    sigma = 4 * math.sqrt(math.pi / 4 * (1 - math.pi / 4))
    ax_err.loglog(k, sigma / np.sqrt(k), color=INK, linewidth=1,
                  linestyle="--", label=r"$\sigma/\sqrt{N}$")
    ax_err.set_xlabel("samples N", color=MUTED)
    ax_err.set_ylabel("absolute error", color=MUTED)
    ax_err.set_title("Error shrinks as $N^{-1/2}$", color=INK, loc="left",
                     fontsize=11)
    ax_err.legend(loc="lower left", frameon=False, fontsize=9)

    fig.suptitle(
        rf"Monte Carlo $\pi$ = {4 * inside.mean():.5f} "
        rf"$\pm$ {err[-1]:.5f}    (true $\pi$ = {math.pi:.5f})",
        color=INK, fontsize=14, x=0.01, ha="left",
    )
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", "--samples", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="pi_monte_carlo.png")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    xy, inside = sample(args.samples, rng)
    estimate = 4 * inside.mean()
    p = inside.mean()
    stderr = 4 * math.sqrt(p * (1 - p) / args.samples)
    z = abs(estimate - math.pi) / stderr

    print(f"samples   {args.samples:,}")
    print(f"estimate  {estimate:.6f} +/- {stderr:.6f}")
    print(f"error     {estimate - math.pi:+.6f}  ({z:.2f} sigma)")
    # A fair sampler lands within 3 sigma of pi 99.7% of the time.
    assert z < 3, "estimate is more than 3 sigma from pi; check the sampler"

    plot(xy, inside, args.out)
    print(f"saved     {args.out}")


if __name__ == "__main__":
    main()
