FROM python:3.11-slim

# התקנות בסיס
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgbm1 \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# התקנת Chrome (גרסה יציבה)
RUN curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt install -y ./chrome.deb && \
    rm chrome.deb

# העתקת קבצי האפליקציה
WORKDIR /app
COPY . .

# התקנת תלויות Python
RUN pip install --no-cache-dir -r requirements.txt

# הגדרת משתנים חשובים
ENV PYTHONUNBUFFERED=1

# הפעלת האפליקציה
CMD ["gunicorn", "flask_app:app", "--bind", "0.0.0.0:5000", "--timeout", "300"]
