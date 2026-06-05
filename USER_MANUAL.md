# Forex Tracker Pro Ultimate - User Manual

## Overview

Forex Tracker Pro Ultimate is a Streamlit-based trading journal and analytics tool built for forex traders. It combines trade logging, performance dashboards, analytics, risk tracking, compounding simulation, goal setting, and trading psychology tracking.

## Getting Started

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app locally

```bash
streamlit run sustainable_forex_journal.py
```

### Access requirements

When the app starts, a subscription gate may require one of the following:

- a valid subscription key
- a direct subscription payment URL
- a subscription backend URL that generates a checkout session

If you do not have a key, use the sidebar link to subscribe.

## Subscription Access

### Entering your subscription key

1. Open the sidebar.
2. Enter your paid subscription key.
3. Click `Unlock app`.

If the key is valid, the app continues to the main dashboard.

### Subscription links

The app supports these configuration values:

- `SUBSCRIPTION_PAYMENT_LINK` or `subscription_payment_link`
  - direct checkout URL or payment page
- `SUBSCRIPTION_BACKEND_URL`
  - backend endpoint that returns a Stripe Checkout session URL (or another provider checkout URL)

If a backend is configured, the sidebar will show a `Generate checkout link` button.

## Main Navigation

The app has seven tabs:

1. `📊 Dashboard`
2. `📖 Journal`
3. `📈 Analytics`
4. `🛡 Risk`
5. `💰 Compounding`
6. `🎯 Goals`
7. `🧠 Psychology`

## Dashboard Tab

This tab gives you a quick summary of your trading performance.

### KPIs

- Net Profit
- Trades
- Win Rate
- Profit Factor
- Expectancy
- Average R
- Largest Win
- Largest Loss
- Avg Winner
- Avg Loser
- Max Drawdown
- Recovery Factor
- Wins
- Losses
- Max Win Streak
- Max Loss Streak

### Charts

- Equity Curve
- Drawdown Curve
- Monthly Profit Bar Chart

## Analytics Tab

This tab provides deeper performance analysis.

### Included reports

- Symbol Leaderboard
- Session Performance
- Setup Performance
- Setup Quality Score
- Direction Analysis
- R-Multiple Distribution
- Duration vs Profit
- Mistake Analysis
- Tag Performance
- Daily Profit Calendar
- Top 10 Trades
- Worst 10 Trades

## Journal Tab

This is where you log new trades and review history.

### Trade form fields

#### Trade Information

- Trade Date
- Symbol
- Direction
- Entry Price
- Exit Price
- Lot Size
- Profit ($)

#### Risk Management

- Risk Amount ($)
- Stop Loss
- Take Profit
- Calculated R Multiple

#### Risk Reflection Questionnaire

Use the Risk tab to answer a built-in questionnaire that helps you reflect on your trading motivation, financial vision, compounding strategy, trader identity, and commitment.

- Saved responses are stored in the Psychology tab under Psychology History.

- Part 1: YOUR WHY
  - Why do you want to learn trading?
  - What attracted you to trading in the first place?
  - What would becoming a consistently profitable trader mean for your life?
  - What problems would trading solve for you?
  - Who would benefit if you became successful?
  - What happens if nothing changes over the next 5 years?
  - Why is now the right time to commit to this journey?
- Part 2: YOUR FINANCIAL VISION
  - What is your current trading account size?
  - What account size would make you feel proud of your progress 12 months from now?
  - What account size would completely change your life?
  - If you could consistently earn 3% per week, what would that mean to you?
  - How much monthly income would make a meaningful difference in your life?
  - What would you do with your first profitable month?
  - What would you do with your first funded payout?
  - What would financial freedom look like for you personally?
- Part 3: THE POWER OF COMPOUNDING
  - Where could your account be in 1 year?
  - Where could your account be in 3 years?
  - How would your life change if you focused on consistency instead of quick profits?
  - What becomes possible when you stop gambling and start compounding?
- Part 4: YOUR FUTURE TRADER IDENTITY
  - Describe the trader you want to become.
  - How does that trader manage risk?
  - How does that trader handle losses?
  - How does that trader approach winning trades?
  - What habits does that trader have?
  - What habits must you stop immediately?
  - What habits must you start building today?
  - How would your future self behave differently from your current self?
- Part 5: COMMITMENT
  - What are you willing to sacrifice over the next 90 days?
  - What distractions are holding you back?
  - On a scale of 1–10, how committed are you to becoming a disciplined trader?
  - What would make that commitment a 10?
  - What promise are you making to yourself today?

#### Session Tracking

- Trading Session: Asian, London, London Open, New York, New York Open

#### Timing

- Entry Time
- Exit Time
- Trade Duration is automatically calculated in minutes

#### Primary Setup

- Setup type selection (e.g. Order Block, Breaker Block, FVG, iFVG, CHoCH, BOS, SMT, Liquidity Sweep, CISD, CRT)

#### ICT Setup Quality Score

- Liquidity Sweep
- HTF Bias
- FVG Present
- CISD Confirmed
- Correct Session
- Displacement

The app calculates a setup score and grade automatically.

#### Trade Tags

Choose tags such as Liquidity Sweep, FVG, iFVG, Order Block, Breaker, SMT, CISD, CRT, News, London Open, New York Open, Continuation, Reversal, Scalp, Intraday, Swing.

#### Mistake Tracking

Choose mistakes from options like FOMO, Overtrading, Moved Stop Loss, Moved Take Profit, Revenge Trading, Ignored HTF Bias, Early Exit, Late Entry, No Confirmation, Risked Too Much.

#### Screenshot Upload

Upload a PNG, JPG, or JPEG screenshot of the trade.

#### Notes

Enter journal notes for the trade.

#### AI Review

The app generates an AI-style review summary after you enter trade details.

### Saving a trade

Click `💾 Save Trade` to commit the entry to the local database. The app will refresh and include the new trade in history and analytics.

### Trade Replay

After saving, select a trade from the dropdown to view:

- symbol
- profit
- R multiple
- session
- setup score
- screenshot
- AI review

### Trade History

The app shows recent trade history with columns including date, symbol, direction, profit, R multiple, session, setup score, and duration.

## Compounding Tab

Use the compounding simulator to model account growth.

### Inputs

- Initial Balance ($)
- Percent Return per Period
- Number of Periods
- Add per Period ($)

The chart and table display projected balance growth and final balance.

## Goals Tab

Track your trading goals with progress tracking.

### Actions

- Add a goal with description, target date, and progress percentage
- Update progress with sliders
- Remove goals

## Psychology Tab

Track your mindset, mood, and reflections.

### Entries

- Select your mood
- Answer reflection prompts
- Add psychology notes

Notes are saved in the session state and displayed in reverse chronological order.

## Configuration and Data

### Local database

The app stores trades in `forex_tracker.db`.

### Screenshots

Uploaded screenshots are saved into the `screenshots/` folder.

### Secrets and environment variables

You can configure the app with secrets or environment variables.

#### Subscription values

- `VALID_SUBSCRIPTION_KEYS`
- `valid_subscription_keys`
- `valid_subscription_keys.txt`
- `SUBSCRIPTION_PAYMENT_LINK`
- `SUBSCRIPTION_BACKEND_URL`

#### Optional Streamlit secret values

- `valid_subscription_keys`
- `subscription_payment_link`

## Deployment

For deployment, use Streamlit Cloud or any Streamlit-compatible host.

### Streamlit Cloud setup

1. Upload the repository or connect your Git provider.
2. Add secrets via the app settings.
3. Optionally configure a backend server to generate Stripe Checkout URLs.

## Troubleshooting

- If the app refuses to unlock, verify your subscription key and secrets.
- If checkout link generation fails, verify `SUBSCRIPTION_BACKEND_URL` and backend availability.
- If screenshots do not upload, confirm `screenshots/` is writable.
- If the app fails to save trades, make sure `forex_tracker.db` is not locked by another process.

## Support

For additional assistance, review the code in `sustainable_forex_journal.py` or contact your developer.
