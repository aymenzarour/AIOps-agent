FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --upgrade google-generativeai

COPY agent.py .

CMD ["python", "agent.py"]