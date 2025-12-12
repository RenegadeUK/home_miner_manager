# v0 Miner Controller

Modern, Dockerized ASIC miner management platform with energy-based automation and Octopus Agile pricing integration.

## Supported Miners

- **Avalon Nano 3 / 3S** - cgminer TCP API (port 4028)
- **Bitaxe 601** - REST API
- **NerdQaxe++** - REST API
- **NMMiner ESP32** - UDP telemetry + config (lottery miner)

## Features

- 📊 **Real-time Telemetry** - Monitor hashrate, temperature, power consumption, and shares
- 🌊 **Pool Management** - Configure and switch between mining pools
- ⚡ **Smart Automation** - Rule-based automation with triggers and actions
- 💡 **Octopus Agile Pricing** - Automatic energy price tracking (no API key required)
- 📡 **MQTT Export** - Export telemetry to MQTT broker
- 🎨 **Modern UI** - Clean v0-inspired design with sidebar navigation

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd home_miner_manager
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start the container:
```bash
docker-compose up -d
```

4. Access the web interface:
```
http://localhost:8080
```

### Manual Docker Build

```bash
docker build -t v0-miner-controller .
docker run -d \
  -p 8080:8080 \
  -v ./config:/config \
  -e WEB_PORT=8080 \
  -e TZ=UTC \
  --name miner-controller \
  v0-miner-controller
```

## Configuration

All configuration is stored in the `/config` volume:

```
/config
├── config.yaml      # Main configuration file
├── data.db          # SQLite database
└── logs/           # Application logs
```

### Environment Variables

- `WEB_PORT` - Web interface port (default: 8080)
- `TZ` - Timezone (default: UTC)
- `PUID` - User ID for file permissions (default: 1000)
- `PGID` - Group ID for file permissions (default: 1000)

## Architecture

```
/app
├── main.py              # FastAPI application entry point
├── core/               # Core services
│   ├── config.py       # Configuration management
│   ├── database.py     # SQLite models and session
│   ├── mqtt.py         # MQTT client
│   └── scheduler.py    # APScheduler for periodic tasks
├── adapters/           # Miner adapters
│   ├── base.py         # Base adapter interface
│   ├── avalon_nano.py  # Avalon Nano 3/3S
│   ├── bitaxe.py       # Bitaxe 601
│   ├── nerdqaxe.py     # NerdQaxe++
│   └── nmminer.py      # NMMiner ESP32
├── api/                # REST API endpoints
│   ├── miners.py       # Miner management
│   ├── pools.py        # Pool management
│   ├── automation.py   # Automation rules
│   └── dashboard.py    # Dashboard stats
└── ui/                 # Web interface
    ├── routes.py       # Jinja2 template routes
    ├── templates/      # HTML templates
    └── static/         # CSS/JS assets
```

## API Documentation

Once running, visit:
- API Docs: `http://localhost:8080/docs`
- Health Check: `http://localhost:8080/health`

### Key Endpoints

**Miners:**
- `GET /api/miners/` - List all miners
- `POST /api/miners/` - Add new miner
- `GET /api/miners/{id}/telemetry` - Get current telemetry
- `POST /api/miners/{id}/mode` - Set operating mode
- `POST /api/miners/{id}/restart` - Restart miner

**Pools:**
- `GET /api/pools/` - List all pools
- `POST /api/pools/` - Add new pool

**Automation:**
- `GET /api/automation/` - List all rules
- `POST /api/automation/` - Create new rule

**Dashboard:**
- `GET /api/dashboard/stats` - Overall statistics
- `GET /api/dashboard/energy/current` - Current energy price
- `GET /api/dashboard/energy/timeline` - Price timeline

## Miner-Specific Notes

### Avalon Nano 3 / 3S
- Uses cgminer TCP API on port 4028
- Power calculation: `watts = raw_power_code / (millivolts / 1000)`
- Modes: `low`, `med`, `high`

### Bitaxe 601 / NerdQaxe++
- REST API with native power/frequency/temperature
- Modes: `eco`, `standard`, `turbo`, `oc`

### NMMiner ESP32
- **Telemetry only** via UDP broadcast (port 12345)
- Config via UDP (port 12347)
- No power metrics or tuning available
- Pool control only (IP "0.0.0.0" = broadcast to all)

## Octopus Agile Integration

1. Go to **Energy Pricing** page
2. Select your region (A-P)
3. System automatically fetches half-hourly prices from Octopus API
4. No API key required - uses public tariff data

## Automation Examples

### Price-Based Mining
```json
{
  "trigger": {
    "type": "price_threshold",
    "threshold": 10
  },
  "action": {
    "type": "apply_mode",
    "mode": "eco"
  }
}
```

### Time-Based Profiles
```json
{
  "trigger": {
    "type": "time_window",
    "start": "02:00",
    "end": "07:00"
  },
  "action": {
    "type": "apply_mode",
    "mode": "turbo"
  }
}
```

## Development

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Testing

```bash
# Run with test config
CONFIG_DIR=./test_config python app/main.py
```

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.
