FROM node:20-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV TESSDATA_PREFIX=/app/tessdata

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libvips-dev \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --production

COPY . .
COPY tessdata /app/tessdata

CMD ["npm", "start"]
