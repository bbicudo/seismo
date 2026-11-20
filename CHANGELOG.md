# Changelog

All notable changes to Seismo are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and versions follow [Semantic Versioning](https://semver.org/). Each version has a matching git tag (`vX.Y.Z`).

## [Unreleased]

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

[Unreleased]: https://github.com/bbicudo/seismo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bbicudo/seismo/releases/tag/v0.1.0
