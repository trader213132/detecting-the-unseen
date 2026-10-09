"""All the settings for the simulated market and the experiment, in one place.

Units: prices are whole numbers of "ticks" (the smallest price step) and time
is whole numbers of "steps". One step is roughly a fraction of a second of
real trading.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class MarketConfig:
    steps: int = 2000             # length of one simulated trading session
    bar_steps: int = 5            # features are summarised over "bars" of this many steps
    depth_levels: int = 5         # how many price levels of each side of the book we look at

    # Fundamental value: the "true" worth of the asset. It follows a random walk
    # that is slowly pulled back towards fundamental_mean.
    fundamental_mean: float = 1000.0
    mean_reversion: float = 0.005
    fundamental_vol: float = 0.5  # typical change per step, in ticks
    jump_prob: float = 0.0        # chance per step of a sudden "news" jump
    jump_size: float = 0.0        # typical size of a jump, in ticks

    # Background traders arrive at random (Poisson) each step.
    arrival_rate: float = 1.5     # average arrivals per step
    reactive_share: float = 0.5   # fraction of arrivals who read the order book
    obs_noise: float = 2.0        # traders only see the fundamental value with this much noise
    surplus_min: float = -2.0     # how far inside/outside their value traders price orders;
    surplus_max: float = 8.0      # a negative surplus means "willing to cross the spread"
    size_p: float = 0.3           # order size ~ Geometric(size_p): mostly 1-4 lots, occasionally more
    mean_patience: float = 50.0   # average steps before an unfilled order is cancelled

    # Reactive traders: how strongly order-book imbalance moves them.
    # This is the behaviour a spoofer exploits.
    react_shift: float = 6.0      # ticks added to their value estimate per unit of imbalance
    react_bias: float = 0.3       # extra probability of choosing to buy per unit of imbalance

    # Market makers quote both sides and constantly cancel and replace their quotes.
    n_market_makers: int = 2
    mm_period: int = 5            # requote every this many steps
    mm_half_spread: int = 1       # distance of their best quotes from their value estimate
    mm_levels: int = 3            # how many price levels they quote on each side
    mm_size: int = 3              # lots per quote
    mm_react_shift: float = 3.0   # market makers also read the book: ticks of quote shift per unit imbalance

    # An "institution" occasionally rests a genuinely large order behind the best price.
    institution_rate: float = 1 / 2000      # chance per step (about one per session)
    institution_life: tuple = (150, 400)    # how long it leaves the order, in steps

    # Accounts: who placed each order, as a regulator (not the public) would see it.
    # Background traders are drawn from a pool of accounts. Account numbers come from
    # their own random stream, so changing them never changes the market itself.
    accounts_per_kind: int = 200            # accounts shared by ZI traders, and again by reactive traders
    omnibus_share: float = 0.0              # share of background orders routed through one broker account;
                                            # if above zero, the spoofer trades through that account too
    spoofer_accounts: int = 1               # 2 = an evasive spoofer: wall from one account, small order from another


# Market regimes. "volatile" has a jumpier fundamental value and wider market-maker quotes.
REGIMES = {
    "calm": MarketConfig(),
    "volatile": replace(MarketConfig(), fundamental_vol=1.5, jump_prob=0.003,
                        jump_size=15.0, mm_half_spread=2),
}

# --- Spoofing episodes (only ever used in TEST sessions) ---------------------
TYPICAL_SIZE = 3            # spoof sizes are multiples of one typical order
MAX_EPISODE_STEPS = 30      # a spoof "wall" is never left on the book longer than this
LAYERS = 4                  # a layered spoof splits its wall over this many price levels
SIZE_MULTIPLIERS = (1, 2, 4, 8, 16)
CONTROL_LIFE = (150, 400)   # legitimate large orders in control sessions stay this long
REVERSAL_AFTER = (5, 25)    # an honest trader who changes their mind does so this many steps after placing

# --- Detection ----------------------------------------------------------------
# The rule-writer's definition of a "quick" cancellation. This is domain
# knowledge: the 2025 Upper Tribunal decision describes spoof orders being
# cancelled within seconds.
FAST_CANCEL_STEPS = 50
TARGET_FPR = 0.01           # alert thresholds are set so ~1% of normal bars alert
