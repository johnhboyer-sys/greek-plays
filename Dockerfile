# The whole site, built from this checkout and served by Caddy.
#
#   docker build -t greek-plays .
#   docker run --rm -p 8080:80 greek-plays      # http://localhost:8080
#
# The build stage is the build of ARCHITECTURE.md with its tools pinned: Node,
# Python by way of uv, and the two outside inputs fetched by checksum. It
# needs the network (npm, PyPI, a Python build, the Diogenes release) and
# nothing from the machine it runs on: each play's Greek is corpus/greek/. The
# serve stage is a static file server on port 80; TLS is the host's business.
# There is no /api here, so the feedback form stays hidden (the bundle leaves
# out the file that would show it). .github/workflows/image.yml builds this
# and asks the running container for every file (scripts/check-served.mjs).

FROM node:22.23.5-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
WORKDIR /src
COPY . .
ENV DIOGENES_DATA=/inputs
# The deploy's settings: every Greek edition, and the primary's origin for the
# canonical links (a mirror's pages name the primary site).
ENV DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1 PUBLIC_SITE_ORIGIN=https://greekdrama.johnhboyer.com
RUN cd pipeline && uv sync && uv run python -m drama_pipeline.inputs fetch --dir /inputs
RUN cd app && npm ci
RUN npm run build:public
# The bundle step runs the data gates and leaves out the files that belong to
# the primary host. What is served is the bundle unpacked, SHA256SUMS and all.
RUN node scripts/make-bundle.mjs --out=/bundle.tar.gz && mkdir /site && tar -xzf /bundle.tar.gz -C /site

FROM caddy:2.11.9-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /site /srv
