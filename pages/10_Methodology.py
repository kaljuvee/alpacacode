"""
Strategy Methodology
Comprehensive documentation of all trading strategies available in the simulator
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Strategy Methodology",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Strategy Methodology")
st.markdown("Comprehensive guide to all trading strategies available in this simulator")

# Table of Contents
st.markdown("---")
st.header("📑 Table of Contents")

toc_col1, toc_col2 = st.columns(2)

with toc_col1:
    st.markdown("""
    - [Buy-The-Dip Strategy](#buy-the-dip-strategy)
    - [Momentum Strategy](#momentum-strategy)
    """)

with toc_col2:
    st.markdown("""
    - [VIX Fear Index Strategy](#vix-fear-index-strategy)
    - [Box & Wedge Strategy](#box-wedge-strategy)
    """)

st.markdown("---")

# Buy-The-Dip Strategy
st.header("Buy-The-Dip Strategy")
st.markdown("""
### Overview
The Buy-The-Dip strategy capitalizes on short-term price pullbacks in trending stocks. It identifies when a stock has dropped by a specified percentage from its recent high and enters a long position, anticipating a bounce back.

### Entry Rules
- **Trigger**: Stock price drops by the dip threshold percentage from its recent high (lookback period: 20 periods)
- **Example**: If dip threshold is 2%, buy when price is 2% below the 20-period high

### Exit Rules
The strategy uses multiple exit conditions:
1. **Take Profit**: Exit when price reaches the take profit percentage above entry
2. **Stop Loss**: Exit when price falls below the stop loss percentage below entry
3. **Time-Based**: Exit after holding for the specified number of days/periods

### Parameters
- **Dip Threshold (%)**: Percentage drop from recent high to trigger buy (default: 2%)
- **Hold Days**: Number of days/periods to hold position (default: 1)
- **Take Profit (%)**: Percentage gain to take profit (default: 1%)
- **Stop Loss (%)**: Percentage loss to stop out (default: 0.5%)
- **Position Size (%)**: Percentage of capital to allocate per trade (default: 10%)

### Use Cases
- **Best For**: Stocks in strong uptrends with occasional pullbacks
- **Market Conditions**: Bull markets or trending stocks
- **Timeframes**: Works on daily and intraday timeframes
- **Risk Profile**: Moderate risk with defined stop losses

### Key Considerations
- Works best in trending markets; avoid in choppy/sideways markets
- Requires discipline to stick to stop losses
- Can generate frequent trades in volatile markets
""")

st.markdown("---")

# Momentum Strategy
st.header("Momentum Strategy")
st.markdown("""
### Overview
The Momentum strategy identifies stocks showing strong upward price movement and enters positions to ride the trend. It assumes that stocks in motion tend to stay in motion.

### Entry Rules
- **Trigger**: Stock price increases by the momentum threshold percentage over the lookback period
- **Example**: If momentum threshold is 5% and lookback is 20 days, buy when price is up 5%+ over the past 20 days

### Exit Rules
Similar to Buy-The-Dip, the strategy uses multiple exit conditions:
1. **Take Profit**: Exit when price reaches the take profit percentage above entry
2. **Stop Loss**: Exit when price falls below the stop loss percentage below entry
3. **Time-Based**: Exit after holding for the specified number of days/periods

### Parameters
- **Lookback Period (days)**: Days to look back for momentum calculation (default: 20)
- **Momentum Threshold (%)**: Minimum momentum percentage to trigger buy (default: 5%)
- **Hold Days**: Number of days to hold position (default: 5)
- **Take Profit (%)**: Percentage gain to take profit (default: 10%)
- **Stop Loss (%)**: Percentage loss to stop out (default: 5%)
- **Position Size (%)**: Percentage of capital per trade (default: 10%)

### Use Cases
- **Best For**: Trending stocks with strong momentum
- **Market Conditions**: Bull markets, breakout scenarios
- **Timeframes**: Daily and weekly timeframes work best
- **Risk Profile**: Moderate to high risk; momentum can reverse quickly

### Key Considerations
- Momentum can be a self-fulfilling prophecy in the short term
- Watch for momentum exhaustion signals
- Works best when combined with volume confirmation
- Avoid during market reversals or high volatility
""")

st.markdown("---")

# VIX Strategy
st.header("VIX Fear Index Strategy")
st.markdown("""
### Overview
The VIX Fear Index strategy uses the CBOE Volatility Index (VIX) as a contrarian indicator. When fear is high (VIX elevated), the strategy buys stocks, anticipating a bounce as fear subsides.

### Entry Rules
- **Trigger**: VIX closes above the specified threshold (default: 20)
- **Rationale**: High VIX indicates elevated fear and potential oversold conditions

### Exit Rules
- **Hold Overnight**: Exit on the next trading day's close
- **Same Day**: Exit on the same day's close (if hold_overnight is False)

### Parameters
- **VIX Threshold**: VIX level to trigger buy (default: 20)
- **Hold Overnight**: Whether to hold overnight (True) or sell same day (False)
- **Position Size (%)**: Percentage of capital to allocate per trade (default: 10%)

### Use Cases
- **Best For**: Contrarian traders looking to buy during panic
- **Market Conditions**: Market corrections, flash crashes, high volatility events
- **Timeframes**: Daily timeframe
- **Risk Profile**: High risk; catching falling knives

### Key Considerations
- VIX can stay elevated for extended periods
- Not all VIX spikes result in immediate bounces
- Works best when combined with other technical indicators
- Requires strong risk management
""")

st.markdown("---")

# Box & Wedge Strategy
st.header("Box & Wedge Strategy")
st.markdown("""
### Overview
The Box & Wedge strategy is based on Christian Carion's methodology for trading index futures (ES, NQ). It identifies periods of price contraction (boxes) and enters on breakouts of tighter contractions within those boxes (wedges), allowing for extremely tight stop losses and high reward-to-risk ratios.

### Christian Carion's Philosophy
Christian Carion uses index futures to generate cash flow, which is then moved into a swing trading portfolio for long-term growth. His approach emphasizes:
- **Risk Management**: 1% account risk per trade (the "All-In" concept)
- **Fractal Market Structure**: Using multiple timeframes to identify setups
- **Scale-Out Approach**: Taking profits in stages while letting runners capture large moves

### The Box & Wedge Framework

#### 1. Box Identification (Contraction Period)
- **Definition**: A period where price is "ping-ponging" in a range, showing low volatility
- **Detection**: Recent price range is less than 70% of the average historical range
- **Timeframe**: Typically identified on hourly charts
- **Purpose**: Identifies consolidation before the next move

#### 2. Wedge Identification (Tighter Contraction)
- **Definition**: A tighter contraction within the box, showing lower highs and higher lows
- **Detection**: Price range within the wedge is less than 60% of the box range
- **Timeframe**: Typically 20 periods within the box
- **Purpose**: Provides the precise entry trigger

#### 3. Entry Trigger
- **Signal**: Breakout of the wedge high (NOT the full box breakout)
- **Advantage**: Tighter stop loss (at wedge low) vs. waiting for box breakout
- **Confirmation**: Entry should align with the hourly trend (EMA 9 > EMA 20)

### Risk Management & Position Sizing

#### The "All-In" Concept
- **Definition**: 100% invested in a single position while keeping total account risk at ~1%
- **Calculation**: Position size = (Account Capital × 1%) / (Entry Price - Stop Price)
- **Result**: Larger position sizes with extremely tight stops

#### Stop Loss Placement
- **Initial Stop**: At the wedge low (below the tighter contraction)
- **Move to Breakeven**: After 1.5R target is hit
- **Trailing Stop**: Optional for runners

### Scale-Out Approach

The strategy takes profits in three stages:

1. **50% at 1.5R** (1.5 times the risk)
   - First profit target
   - Locks in gains quickly
   - Moves stop to breakeven for remaining position

2. **25% at 3R** (3 times the risk)
   - Second profit target
   - Captures extended moves
   - Reduces position further

3. **25% Runner**
   - Kept with stop at breakeven
   - Captures large trend moves
   - No fixed target; exit on trend reversal

### Trend Filters

#### Bull/Bear Filter (Daily)
- **Bullish**: Price > 200-day SMA
- **Bearish**: Price < 200-day SMA
- **Action**: Only trade in direction of the daily trend

#### Short-Term Momentum (Hourly)
- **EMA 9 and EMA 20**: Used for trend direction
- **Bullish**: EMA 9 > EMA 20
- **Bearish**: EMA 9 < EMA 20
- **Exit Signal**: Two consecutive closes below EMA 20 often signals trend end

### Zone Rotations

Christian identifies horizontal "zones" where price typically reacts:
- **ES (S&P 500)**: Rotations occur roughly every 12-15 points
- **NQ (Nasdaq)**: Rotations occur roughly every 25-35 points
- **Purpose**: Helps identify potential support/resistance levels

### Parameters
- **Contraction Threshold**: Box contraction threshold (default: 0.7 = 70%)
- **Box Lookback Periods**: Periods to look back for box (default: 100)
- **Wedge Lookback Periods**: Periods to look back for wedge (default: 20)
- **Risk Per Trade (%)**: Percentage of capital to risk (default: 1%)
- **1.5R Target (%)**: Percentage to exit at 1.5R (default: 50%)
- **3R Target (%)**: Percentage to exit at 3R (default: 25%)
- **Runner (%)**: Percentage to keep as runner (default: 25%)

### Use Cases
- **Best For**: Index futures (ES, NQ) or ETF proxies (SPY, QQQ)
- **Market Conditions**: Works in both trending and ranging markets
- **Timeframes**: 2-minute or 5-minute for entries, hourly for trend alignment
- **Risk Profile**: Low risk per trade (1%) with high reward potential

### Key Considerations
- Requires patience to wait for proper box and wedge formation
- Tight stops mean you may get stopped out frequently
- Scale-out approach ensures you capture profits while staying in winners
- Works best when aligned with higher timeframe trends
- Requires discipline to follow the scale-out plan
""")

st.markdown("---")

# Risk Management Principles
st.header("🛡️ Risk Management Principles")
st.markdown("""
### Common Risk Management Across All Strategies

1. **Position Sizing**
   - Never risk more than 1-2% of total capital on a single trade
   - Adjust position size based on stop loss distance
   - Smaller positions in volatile markets

2. **Stop Losses**
   - Always use stop losses to limit downside risk
   - Place stops at logical technical levels
   - Never move stops further away from entry

3. **Take Profits**
   - Have a plan for taking profits before entering
   - Consider scaling out of positions
   - Let runners work in strong trends

4. **Diversification**
   - Don't put all capital in one strategy
   - Trade multiple uncorrelated assets
   - Balance aggressive and conservative strategies

5. **Drawdown Management**
   - Reduce position sizes during drawdown periods
   - Take a break after consecutive losses
   - Review and adjust strategy parameters if needed

6. **Backtesting**
   - Always backtest strategies before live trading
   - Use realistic fees and slippage assumptions
   - Test across different market conditions

7. **Emotional Discipline**
   - Stick to your trading plan
   - Don't revenge trade after losses
   - Don't overtrade after wins
   - Keep a trading journal
""")

st.markdown("---")

# Footer
st.markdown("""
<div style='text-align: center; color: gray;'>
<p>Strategy Simulator | For educational purposes only</p>
<p>Past performance does not guarantee future results</p>
</div>
""", unsafe_allow_html=True)
