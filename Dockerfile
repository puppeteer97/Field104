# Use Node 18 on Debian Bullseye slim
FROM node:18-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Install system deps: tesseract, libleptonica, libvips (for sharp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libleptonica-dev \
    libtesseract-dev \
    libvips-dev \
    pkg-config \
    build-essential \
    ca-certificates \
    wget \
  && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Copy package.json and install (use production by default)
COPY package.json package-lock.json* ./

RUN npm install --production

# Copy app files
COPY . .

# Ensure tessdata dir exists and contains g.traineddata (copied from repo)
RUN mkdir -p /app/tessdata

# Expose nothing (bot runs in background). Start command uses node bot.cjs
CMD ["npm", "start"]
