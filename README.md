# Seismo

*Feel every world shake.*

Seismo is a self-updating Tibia fansite that covers every game world. It collects public data
continuously and turns it into live statistics, maps and monthly summaries, in Portuguese and English.

> Open beta. Data comes from [TibiaData](https://tibiadata.com/). Tibia is a registered trademark of CipSoft GmbH;
> Seismo is a non-profit fan project and is not affiliated with CipSoft.

## Features

**Worlds** (each world page is split into tabs, so no page gets too long and nothing is shown twice)
- **Overview** of all worlds: players online right now, 48-hour chart, top deaths, and a worlds table that can be
  sorted by players online, health index or trend, and filtered by region and PvP type.
- **Health index** (0 to 100): ranks every world by its online trend, how many players come back, new characters
  and net transfers, comparing the last 7 days with the 7 before. Weights and window are adjustable in `/admin`.
- **World health**: hourly average and peak of players over 7, 14 or 30 days, all-time record, event days shaded.
- **Transfer flows**: which worlds characters came from and went to.
- **Activity heatmap**: average players online by weekday and hour, filterable by vocation and level band.
  Anonymous aggregates only; event days (double XP, rapid respawn) are excluded by default.
- **Vocations**: average players online by vocation and level band, share of each vocation and its change
  against the previous week.
- **Leveling speed**: levels gained per hour online by vocation and level band.
- **Newcomer funnel**: characters created per day and how many reach levels 8, 20, 50 and 100.
- **Newcomer retention**: share of each weekly class still playing after 7, 30 and 90 days.

**Characters**
- **Character page**: level, hours online per day, levels per month, guild, houses and transfers (no login times).
  Not indexed by search engines by default.

**Hunting and raids**
- **Top deaths**: worlds with the most players killed by creatures on the last day.
- **Hunt map**: the game map with the busiest hunting areas of the day, drawn from kill statistics
  (329 hunting areas from TibiaWiki), with each area's change against the previous days and a risk index
  (players killed per thousand creatures killed).
- **Creatures of the day** per world, with the same change and risk columns.
- **Raids**: raids detected from kill statistics (47 detectable raids out of 116 listed on TibiaWiki), how often
  each one happens and a likely next window, flagged when it is open now or overdue.
- **Respawn thermometer**: creatures with unusually high or low kills compared with the previous 28 days
  (spot likely crowded or likely free), with the daily boosted creature flagged.

**Guilds and houses**
- **Guild vitality**: per world, each guild's members, share of members active in the last 7 days, net joins and
  departures, and average level, sortable by each of them.
- **Member exchange between guilds**: guild pairs with the most members leaving one and joining the other
  (totals only, shown from 5 people up).
- **Guild page**: members, rank, level, founding date, war status, vocation mix, joins/departures over time and a
  heatmap of when the guild plays (guilds with 15+ members only).
- **House market**: per town, occupancy, open auctions, average bid, auctions closed, median days to rent and owner
  changes; every house by town with current owner and owner history.

**Events**
- **Game events**: double XP, double skill and rapid respawn read from official tibia.com news; full moon and
  seasonal events from a community calendar.
- **Today in Tibia**: boosted creature, boosted boss and active events.
- **Event impact**: how much each double XP, double skill or rapid respawn changes players online, creatures killed
  and players killed across all worlds, against the same weekdays in the weeks before.
- **Boosted creature effect**: how many times more the boosted creature is hunted than on a usual day.

**Wrapped**
- **Monthly summaries** for a character, a guild or a world: hours online, days played, levels gained, rank within
  the world, top creatures and more.
- **Share buttons** (copy link, WhatsApp, Facebook, X, Discord, Instagram) and preview images that show up
  automatically when a link is pasted into Discord, WhatsApp or social apps.

**Utils**
- **Selling loot to Yasir**: every item Yasir buys, with what he pays and whether it is safe to sell, only worth
  selling if you skip the weekly Delivery Task, or worth more kept (quest, addon, imbuement, market), with search and
  filters, the quest, addon or imbuement each item is used for, and item sprites loaded by the browser from
  TibiaWiki. Data from TibiaWiki (CC BY-SA). Flags `page_utils` (the whole area) and `util_yasir`.

- **Hunting areas**: hunts tested by [TibiaPal](https://tibiapal.com/hunting) (by Kusnier)
  for each vocation, with minimum level, raw exp and loot per hour, recommended weapon, ammo or playstyle and the test
  video, filtered by vocation, town and level and sorted by level, exp or loot. Each hunt's page adds its monsters
  from TibiaWiki (sprites, HP, exp, weaknesses and the damage they deal), the recommended damage type (average of the
  monsters' elemental weaknesses) and the recommended protections (each element's share of the monsters' maximum
  damage). Data built by `tools/build_hunt_areas.py` and `tools/build_hunt_places.py`. Flag `util_hunts`.

**Privacy and administration**
- **Opt-out**: a character owner proves ownership with a code in the character comment on tibia.com; the name then
  disappears from the site, the data tied to it is deleted and it is no longer recorded.
- **About** and **Privacy** pages in both languages.
- **Admin area** (`/admin`, separate login): feature flags to turn each part of the site and each collection on or
  off, and adjustable parameters (daily request cap, pace, privacy thresholds, SEO, thermometer, raid tuning and
  every insight window, weight and threshold).
- **BattlEye filter** on the world list: green (protected since launch) or yellow (added later), read from
  TibiaData's `battleye_date` (flag `filter_battleye`).
- **Mobile cards**: on phones, wide tables (hunts, raids, guilds, houses, event impact) turn into one card per row,
  with each number labelled by its column (flag `ui_mobile_cards`).
- **Suggest a fix**: "Found a mistake?" link in the footer and on the utils pages, with a form to pick the tool (or
  "another part of the site") and describe the mistake; suggestions show up in `/admin`, no name, e-mail or IP is
  stored and each visitor is limited per hour (flag `feedback_form`, parameter `feedback_per_hour`).
- **SEO**: sitemap, robots, canonical and pt/en alternate links, and a preview image for every page.
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
- Insights (vocations, leveling speed, retention, guild exchanges) are totals only; groups under 5 people are hidden.
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

## License

Seismo is free software, licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).
You can use, study, modify and share it. If you run a modified version as a public website or service, you must
make your modified source code available to its users under the same license.

Third-party data and assets keep their own terms (see Credits): TibiaWiki content is CC BY-SA 3.0 and the game map
is © CipSoft GmbH.

## AI disclaimer

This whole project, including code, infrastructure and documentation, is developed with the support of AI.
