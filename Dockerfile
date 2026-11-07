FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS download
ARG TARGETARCH
ARG PAIR_VERSION=1.0.0
ARG PAIR_SHA256=94a7d86805c9297fd0dd07b288176955273e8c98ab65fa8848f520e8081f2c54
COPY container/fetch.py /fetch.py
RUN test "$TARGETARCH" = amd64 && python3 /fetch.py "$PAIR_VERSION" "$PAIR_SHA256" /bundle

FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
WORKDIR /app
COPY --from=download /bundle/ /app/
COPY container/supervisor.py container/admin.py container/entrypoint.py /app/
COPY third-party/ /usr/share/licenses/nvpair/
COPY LICENSE /usr/share/licenses/nvpair/LICENSE
RUN chmod 0755 /app/nvpair-* /app/inference-dispatcher
ENV HOME=/state XDG_CONFIG_HOME=/state/config PYTHONUNBUFFERED=1
USER 0:0
HEALTHCHECK --interval=30s --timeout=25s --start-period=90s --retries=3 \
  CMD ["python3", "/app/entrypoint.py", "python3", "/app/supervisor.py", "--health"]
STOPSIGNAL SIGTERM
ENTRYPOINT ["python3", "/app/entrypoint.py"]
