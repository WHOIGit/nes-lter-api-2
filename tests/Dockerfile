FROM node:22-slim

# Required for nodejs 15+
WORKDIR /tests

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    unzip \
    jq \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libasound2 \
    libdrm2 \
    libxshmfence1 \
    libxcomposite1 \
    libxrandr2 \
    libxrender1 \
    libxi6 \
    libxfixes3 \
    libxcursor1 \
    libxdamage1 \
    libgbm1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

COPY ./tests/*.bat /tests/
COPY ./tests/*.js /tests/
COPY ./tests/*.csv /tests/
COPY ./tests/*.xlsx /tests/
COPY ./tests/*.hdr /tests/
COPY ./tests/import/ /tests/import/

RUN npm install selenium-webdriver

# Get Chrome for Testing - Chrome stable version
RUN CHROME_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chrome[] | select(.platform == "linux64") | .url') && \
    curl -sSLf --retry 3 --output /tmp/chrome-linux64.zip "$CHROME_URL" && \
    unzip /tmp/chrome-linux64.zip -d /opt && \
    ln -s /opt/chrome-linux64/chrome /usr/local/bin/chrome && \
    rm /tmp/chrome-linux64.zip

# Get Chromedriver for Testing - matching Chrome version
RUN CHROMEDRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform == "linux64") | .url') && \
    curl -sSLf --retry 3 --output /tmp/chromedriver-linux64.zip "$CHROMEDRIVER_URL" && \
    unzip -o /tmp/chromedriver-linux64.zip -d /tmp && \
    rm -rf /tmp/chromedriver-linux64.zip && \
    mv -f /tmp/chromedriver-linux64/chromedriver "/usr/local/bin/chromedriver" && \
    chmod +x "/usr/local/bin/chromedriver"

RUN chmod +x /tests/RunAllTests-Docker.bat && sed -i 's/\r//' /tests/*.bat
