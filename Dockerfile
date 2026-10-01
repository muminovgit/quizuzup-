# Single image: Telegram bot + web API + the built website, all served by
# one process (render_start.py) so they always share the same SQLite file
# and there's exactly one thing to deploy and keep alive.

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt -r webapi/requirements.txt

RUN cd webapp && npm ci && npm run build

ENV PORT=10000
EXPOSE 10000
CMD ["python", "render_start.py"]
