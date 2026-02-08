FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
	ca-certificates \
	libnss3 \
	libatk1.0-0 \
	libatk-bridge2.0-0 \
	libcups2 \
	libdrm2 \
	libxkbcommon0 \
	libxcomposite1 \
	libxdamage1 \
	libxfixes3 \
	libxrandr2 \
	libgbm1 \
	libpango-1.0-0 \
	libpangocairo-1.0-0 \
	libasound2 \
	libatspi2.0-0 \
	libgtk-3-0 \
	libx11-xcb1 \
	libxshmfence1 \
	libxext6 \
	libx11-6 \
	libexpat1 \
	libfontconfig1 \
	libfreetype6 \
	libglib2.0-0 \
	libgdk-pixbuf-2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN pip install --no-cache-dir -r requirements.txt \
	&& python -m playwright install chromium \
	&& chmod -R 755 /ms-playwright

COPY main.py service.py ./

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["python", "main.py"]
