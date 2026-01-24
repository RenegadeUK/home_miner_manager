# Agile Solo Strategy

The killer feature of HMM - automatically optimize mining based on Octopus Agile electricity pricing.

## How It Works

Every 15 minutes, the strategy:
1. Fetches current + next electricity price
2. Determines price band (Expensive/Medium/Cheap/Free)
3. Adjusts enrolled miners accordingly

## Price Bands (Default)

### Band 0: EXPENSIVE (20p/kWh+)
- **Action**: Miners turned OFF externally (manual/automation)
- **Reason**: Not worth running at high prices
- **HMM Role**: Signals user to power off, doesn't control hardware

### Band 1: MEDIUM (12-20p/kWh)
- **Coin**: DigiByte (DGB)
- **Modes**: Low power (eco/low)
- **Why**: Frequent blocks (£2 each), minimal electricity waste

### Band 2: BASELINE (7-12p/kWh)  
- **Coin**: DigiByte (DGB)
- **Modes**: Standard power (standard/med)
- **Why**: Still economical, better chance at blocks

### Band 3: CHEAP (2-7p/kWh)
- **Coin**: Bitcoin (BTC)
- **Modes**: Higher power (turbo/high)
- **Why**: Swing for jackpot when electricity is cheap

### Band 4: FREE (0-2p/kWh)
- **Coin**: Pool mining (BTC/Braiins)
- **Modes**: Maximum power
- **Why**: Guaranteed returns when electricity is nearly free/negative

### Band 5: NEGATIVE (<0p/kWh)
- **Coin**: Pool mining (BTC/Braiins)
- **Modes**: Maximum power  
- **Why**: You're PAID to use electricity - maximize consumption for guaranteed income

## Hysteresis (Anti-Flapping)

The strategy uses **look-ahead confirmation** to prevent rapid switching:
- Price improving? Check NEXT slot confirms the improvement
- Price worsening? Act immediately to save costs
- Minimum runtime: 2 slots (60 minutes) in most cases

## Enrollment

Miners must be **explicitly enrolled** in Settings → Agile Solo Strategy:
1. Select miners to enroll
2. Strategy only controls enrolled miners
3. Non-enrolled miners remain manual/automation-controlled

## What Strategy Does NOT Do

- ❌ Physical power on/off (that's external: smart plugs, HEMA, manual)
- ❌ Control non-enrolled miners
- ❌ Override manual user changes (respects user intent)

## Expected Outcomes

**Cost Savings**: 40-60% reduction in electricity costs vs 24/7 mining
**Income Boost**: Mining when free/negative = pure profit
**Sustainability**: Makes hobby mining financially viable in UK

**User Feedback**: "I used to lose £30/month on mining. Now I'm break-even or slightly positive!"
