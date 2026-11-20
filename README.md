# Seismo

*Feel every world shake.*

Seismo is a self-updating Tibia fansite that covers every game world. It collects public data
continuously and turns it into live statistics, maps and monthly summaries, in Portuguese and English.

> Open beta. Data comes from [TibiaData](https://tibiadata.com/). Tibia is a registered trademark of CipSoft GmbH;
> Seismo is a non-profit fan project and is not affiliated with CipSoft.

## Features

**Worlds**
- **Overview** of all worlds: players online right now, 48-hour chart, breakdown by region, filters by region and PvP type.
- **World health**: hourly average and peak of players over 7, 14 or 30 days, all-time record, and transfers in/out.
- **Activity heatmap**: average players online by weekday and hour, filterable by vocation and level band.
  Anonymous aggregates only; event days (double XP, rapid respawn) are excluded by default.
- **Who is online now**: anonymous count by vocation and level band.
- **Characters created**: daily count of new characters per world (characters first seen at a low level).

**Hunting and raids**
- **Top deaths**: worlds with the most players killed by creatures on the last day.
- **Most killed creatures** per world.
- **Hunt map**: the game map with the busiest hunting areas of the day, drawn from kill statistics
  (329 hunting areas from TibiaWiki).
- **Raids**: raids detected from kill statistics (47 detectable raids out of 116 listed on TibiaWiki), how often
  each one happens and a likely next window.
- **Respawn thermometer**: creatures with unusually high or low kills compared with the previous 28 days
  (spot likely crowded or likely free), with the daily boosted creature flagged.

**Guilds and houses**
- **Guilds**: members, rank, level, founding date, war status, vocation mix, and joins/departures over time.
- **Houses**: every house by town, rent status, auctions with current bid, current owner and owner history.

**Events**
- **Game events**: double XP, double skill and rapid respawn read from official tibia.com news; full moon and
  seasonal events from a community calendar.
- **Today in Tibia**: boosted creature, boosted boss and active events.

**Wrapped**
- **Monthly summaries** for a character, a guild or a world: hours online, days played, levels gained, rank within
  the world, top creatures and more.
- **Share buttons** (copy link, WhatsApp, Facebook, X, Discord, Instagram) and preview images that show up
  automatically when a link is pasted into Discord, WhatsApp or social apps.

**Privacy and administration**
- **Opt-out**: a character owner proves ownership with a code in the character comment on tibia.com; the name then
  disappears from the site, the data tied to it is deleted and it is no longer recorded.
- **About** and **Privacy** pages in both languages.
- **Admin area** (`/admin`, separate login): feature flags to turn each part of the site and each collection on or
  off, and adjustable parameters (daily request cap, pace, privacy thresholds, thermometer and raid tuning).
- **Daily request cap** (34k by default) that keeps the load on TibiaData predictable.

## How it works

```
TibiaData ──► collector (Python) ──► Redis (who is online right now)
                     │
                     └──────────► PostgreSQL (history and aggregates) ──► API (FastAPI) ──► website (Next.js, pt/en)
                                                                                               │
                                                                                Caddy (HTTPS) ◄┘
```

- **Every 5 minutes:** the world list and each world's online list. Comparing consecutive snapshots yields minutes
  online per game day, monthly levels, transfers and anonymous counters by vocation × level band × hour.
- **Once a day** (after server save): kill statistics, guild lists, houses and auctions, events and boosted creatures.
- **Throughout the day:** guild details (each guild every 3 days) and house owners, within the daily request cap.
- At most 2 concurrent requests and 2 per second, with exponential backoff and `Retry-After` support.

## Privacy

- No per-character login or logout times are stored: only total minutes per day and the last day seen.
- Heatmaps are aggregates only. With a filter, cells with fewer than 5 players are hidden.
- Online/offline status of guild members is not stored.
- Daily minutes per character are kept for 400 days.
- Any character owner can opt out at any time.

## Project layout

| Folder | Contents |
|---|---|
| `collector/` | Python collector (httpx, Redis, psycopg), daily jobs, raid and hunt seeds |
| `api/` | FastAPI API and Alembic migrations |
| `web/` | Next.js website (standalone output), Portuguese and English |
| `infra/` | Caddy, Docker daemon settings, operation, deploy and backup scripts, systemd timers |
| `tools/` | Scripts that rebuild the raid and hunt seeds from TibiaWiki |

## Running

Everything runs with Docker Compose. Images are multi-arch (`linux/amd64` and `linux/arm64`).

```bash
sudo infra/scripts/bootstrap-docker.sh    # installs Docker (Ubuntu 24.04)
infra/scripts/init-env.sh                 # creates .env and the internal Postgres password
infra/scripts/seismo.sh admin-user <name> # login for the /admin area
docker compose up -d --build
infra/scripts/seismo.sh resume            # the collector starts paused
infra/scripts/seismo.sh status
```

Updates: `infra/scripts/deploy.sh` pulls from GitHub, rebuilds what changed and restarts the services.

## Images

GitHub Actions ([`images.yml`](.github/workflows/images.yml)) runs the tests and publishes multi-arch images to the
GitHub Container Registry on every push to `main` and on `v*` tags, building each architecture on a native runner:

- `ghcr.io/bbicudo/seismo-collector`, `ghcr.io/bbicudo/seismo-api`, `ghcr.io/bbicudo/seismo-web`
- tags: `main`, `sha-<commit>` and, for releases, `<version>`

To use the published images instead of building: set `REGISTRY=ghcr.io/bbicudo` and `SEISMO_TAG=main` (or a version)
in `.env`, then run `docker compose pull && docker compose up -d`.

## Credits

- Game data: [TibiaData](https://tibiadata.com/), which reads [tibia.com](https://www.tibia.com/).
- Raid and hunting area lists: [TibiaWiki](https://tibia.fandom.com/), CC BY-SA 3.0.
- Game map: [TibiaMaps](https://tibiamaps.io/); the map itself is © CipSoft GmbH.
- Community event calendar: [TibiaMarket](https://tibiamarket.top/).
- Social icons: [Simple Icons](https://simpleicons.org/), CC0.
- Fonts: Pixelify Sans, IBM Plex Sans and IBM Plex Mono, SIL Open Font License.

## AI disclaimer

This whole project, including code, infrastructure and documentation, is developed with the support of AI.
