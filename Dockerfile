FROM node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c AS build
WORKDIR /app
RUN --network=none chown node:node /app
ENV npm_config_offline=true npm_config_ignore_scripts=true npm_config_registry=http://127.0.0.1:9/ npm_config_audit=false npm_config_fund=false npm_config_update_notifier=false
ENV JITI_FS_CACHE=false JITI_SOURCE_MAPS=false JITI_DEBUG=false COREPACK_ENABLE_NETWORK=0
USER node
COPY --chown=node:node . .
RUN --network=none bash scripts/offline-build.sh

FROM scratch AS artifacts
COPY --from=build /app/dist/ /dist/
COPY --from=build /app/bundle.html /bundle.html
