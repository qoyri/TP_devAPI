FROM elixir:1.15-alpine AS build

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base git

# Install hex and rebar
RUN mix local.hex --force && mix local.rebar --force

# Set build ENV
ENV MIX_ENV=prod

# Install dependencies
COPY mix.exs mix.lock ./
RUN mix deps.get --only prod
RUN mix deps.compile

# Copy application code
COPY config config
COPY lib lib

# Compile application
RUN mix compile

# Build release
RUN mix release

# ============ Runtime ============
FROM alpine:3.18 AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache libstdc++ openssl ncurses-libs

# Copy release from build stage
COPY --from=build /app/_build/prod/rel/oauth2_server ./

ENV HOME=/app
ENV MIX_ENV=prod
ENV PHX_SERVER=true

EXPOSE 4000

CMD ["bin/oauth2_server", "start"]
