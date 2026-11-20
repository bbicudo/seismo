# Contributing to Seismo

Thanks for wanting to help! Seismo is in open beta, so bug reports and ideas are especially welcome.

## Reporting bugs and suggesting features

- Use the issue templates: **Bug report** or **Feature request**. Questions and open ideas go to **Discussions**.
- For bugs, include the page URL, what you expected and what happened, and your device and browser if it is a layout issue.
- Please search existing issues first.
- Security or privacy problems: do **not** open a public issue, see [SECURITY.md](SECURITY.md).
- Want your character removed from the site? Use the opt-out page on the site; no issue needed.

## Development setup

Requirements: Docker with Compose. Python 3.12 and Node 22 are only needed to run parts outside Docker.

```bash
infra/scripts/init-env.sh               # creates .env and secrets/ (never commit them)
docker compose up -d --build
infra/scripts/seismo.sh resume          # the collector starts paused
```

Project layout: `collector/` (Python collector), `api/` (FastAPI and migrations), `web/` (Next.js), `infra/`
(Caddy and scripts), `tools/` (seed builders). The [README](README.md) explains how everything fits together.

## Pull requests

1. Fork the repository and create a branch from `main`: `feature/...` for new features, `fix/...` for bug fixes,
   `enhancement/...` for improvements to something that already exists. Nothing is committed straight to `main`.
2. Keep changes focused: one topic per pull request.
3. Use [Conventional Commits](https://www.conventionalcommits.org/) for messages (`feat:`, `fix:`, `docs:`, `chore:`).
4. Make sure CI passes: the collector self-test (`python -m seismo_collector.selftest` inside `collector/src`),
   the Python syntax checks and the Docker builds for both architectures.
5. Database changes go in a new Alembic migration under `api/migrations/versions/`.
6. Fill in the pull request template.

Releases are tagged `vX.Y.Z` ([Semantic Versioning](https://semver.org/)) and described in
[CHANGELOG.md](CHANGELOG.md); add your change under *Unreleased*.

## Ground rules

- **Privacy first.** Never store per-character login or logout times, never expose groups smaller than the anonymity
  threshold, and keep the opt-out working. Changes that weaken privacy will not be merged.
- **Be gentle with TibiaData.** Respect the daily request cap, the concurrency limit and the backoff. Discuss any new
  collection that adds requests before opening a pull request.
- **No secrets or infrastructure details** in the repository (`.env`, `secrets/`, IPs, keys).
- Text shown on the site must exist in both Portuguese and English (`web/lib/i18n.js`).

By contributing you agree that your contributions are licensed under the project's license and that you follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
