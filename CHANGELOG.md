# Changelog

All notable changes to Seismo are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and versions follow [Semantic Versioning](https://semver.org/). Each version has a matching git tag (`vX.Y.Z`).

## [Unreleased]

### Changed

- **Hunting areas** now list the hunts tested by TibiaPal (tibiapal.com, by Kusnier, used with permission and credit)
  for each vocation, with minimum level, raw exp and loot per hour, recommended weapon, ammo or playstyle and the test
  video; monsters, weaknesses, damage, element and protections still come from TibiaWiki. Vocation tabs, level filter
  by the hunts' own levels and sorting by level, exp or loot.

## [0.4.0] - 2026-11-22

Hunting areas and a way to report mistakes.

### Added

- **Hunting areas** (`/utils/hunts`, flag `util_hunts`): every hunting place on TibiaWiki (438) with search and filters
  (town, best element, vocation and level), and a page per area with the recommended level, exp and loot, the
  recommended damage type (average of the monsters' elemental weaknesses, bosses left out), the recommended
  protections (each element's share of the monsters' maximum damage) and a monster table with sprites, HP, exp,
  weaknesses and the damage they deal. Data built by `tools/build_hunt_areas.py`; sprites and element icons load in
  the browser straight from TibiaWiki.
- **Suggest a fix** (flag `feedback_form`, parameter `feedback_per_hour`): "Found a mistake?" link in the footer, under
  the utils cards and on each tool, with a form to pick the tool or "another part of the site"; suggestions show up in
  `/admin` to resolve or delete. No name, e-mail or IP is stored.

### Changed

- Privacy page mentions the images loaded from TibiaWiki and what the suggestion form keeps.

## [0.3.0] - 2026-11-22

Utils, a BattlEye filter and tables that work on phones.

### Added

- **Utils** area (`/utils`, flag `page_utils`) with its first tool, **Selling loot to Yasir** (flag `util_yasir`):
  every item Yasir buys, what he pays and whether it is safe to sell, only worth selling if you skip the weekly
  Delivery Task, or worth more kept, with the quest, addon or imbuement it is used for, search, filters and item
  sprites loaded by the browser from TibiaWiki.
- **BattlEye filter** on the world list (flag `filter_battleye`): green (since launch) or yellow (added later); the
  world header shows the type too.
- **Mobile cards** (flag `ui_mobile_cards`): on phones, wide tables turn into one card per row, with each number
  labelled by its column and empty rows hidden.

### Changed

- **Hunts ranking**: hunting area and main creatures first, town under the name, compact numeric headers; no sideways
  scrolling on desktop.
- **Other wide tables** (raids, guilds, guild members, town houses, house market, event impact, world list): main
  information first, secondary details under the name.
- **Texts** use the full width of their box; the new-characters vital no longer shows the per-thousand note.
- Switching language keeps the current page, filters and anchor instead of going back to the home page.

## [0.2.0] - 2026-11-21

Numbers that read on their own, and up-to-date dependencies.

### Changed

- **Vital signs**: new characters and transfers shown as plain counts ("arrived / left" instead of a signed net
  balance), with the per-thousand-online value as a note; the header says how many days are left until the health
  index is ready.
- **Hunts**: the risk-per-thousand column became "Players killed (estimate)", with the ratio in a tooltip; columns
  say they count creatures killed and compare with the N-day average.
- **Guilds**: "Played in N days" and "Joined / left (N days)" instead of "Active" and a signed balance.
- **Houses**: units on size and rent (sqm, gp/month), "no bid", time left in Portuguese, "auctions closed".
- **Texts across the site**: every section intro now says only what the data shows; method details live in the
  "How we calculate it" boxes or were dropped.
- **Dependencies**: Node 26, Redis 8.4, Caddy 2.11.9, Postgres 16.15, Python 3.12.16, FastAPI 0.163, uvicorn 0.54,
  alembic 1.20, psycopg 3.3.9, redis-py 8.1, pydantic 2.14 and newer GitHub Actions. Security fixes for next, postcss,
  sharp and orjson.
- The API's `/api` prefix moved to uvicorn's `--root-path` (the FastAPI parameter is deprecated).
- Dependabot no longer opens major upgrades of Postgres, Python minor/major or Next; those need planned migrations.

### Added

- **Admin**: today's collector errors broken down by request type and reason, each with a short explanation.

## [0.1.0] - 2026-11-20

First tagged version: the open beta.

### Added

- **Collector**: online list of every world every 5 minutes; daily kill statistics, guilds, houses and auctions,
  events and boosted creatures; guild details and house owners within a daily request cap (34k by default).
- **Worlds**: overview of all worlds with a 48-hour chart and top deaths; each world page split into tabs
  (overview, activity, hunts, raids, guilds, houses) with a shared header.
- **Insights**: world health index (0–100) and ranking, transfer flows, vocations with weekly change, leveling
  speed (time per level by vocation and level band), newcomer funnel and retention.
- **Activity heatmap** by weekday and hour, filterable by vocation and level band, event days excluded by default.
- **Hunting**: hunt map of the busiest areas of the day, with change against previous days and a risk index;
  creatures of the day.
- **Raids** detected from kill statistics, with frequency, likely next window (in window / overdue) and a respawn
  thermometer.
- **Guilds**: vitality table (active members, net joins, average level), member exchange between guilds, guild page
  with members, joins/departures and a heatmap for guilds with 15+ members.
- **Houses**: market by town (occupancy, auctions, average bid, days to rent, owner changes), town and house pages.
- **Events**: double XP, double skill, rapid respawn and community calendar; Today in Tibia; event impact and
  boosted creature effect.
- **Character page**: level, hours online per day, levels per month, guild, houses and transfers.
- **Wrapped**: monthly summaries for characters, guilds and worlds, with share buttons and preview images.
- **Privacy**: opt-out verified through the tibia.com character comment, About and Privacy pages, totals only
  with groups under 5 hidden, no login times stored.
- **Admin area** (`/admin`, separate login): feature flags for every page section and collection, and adjustable
  parameters (request cap, pace, privacy thresholds, SEO, raids, every insight window and weight).
- **SEO**: sitemap, robots, canonical and pt/en alternate links, preview image on every page.
- **Infrastructure**: Docker Compose stack (PostgreSQL, Redis, FastAPI, Next.js, Caddy with HTTPS), multi-arch
  images (amd64 + arm64) on GHCR, deploy, backup and restore scripts.
- **Project**: AGPL-3.0 license, code of conduct, contributing guide, security policy, issue and PR templates,
  Dependabot.

[Unreleased]: https://github.com/bbicudo/seismo/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/bbicudo/seismo/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/bbicudo/seismo/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bbicudo/seismo/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bbicudo/seismo/releases/tag/v0.1.0
