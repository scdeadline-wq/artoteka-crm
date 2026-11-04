FROM python:3.13-slim

WORKDIR /app

# ffmpeg: голосовые Telegram приходят в OGG/Opus, а MixRoute/Gemini принимает только mp3/wav
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/bot/

ENV PYTHONPATH=/app

CMD ["python", "-m", "bot.main"]
