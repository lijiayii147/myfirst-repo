FROM python:3.11-slim
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY wenmai wenmai
COPY data data
RUN useradd -m wenmai && mkdir runtime && chown wenmai runtime
USER wenmai
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "wenmai.app:app", "--host", "0.0.0.0", "--port", "8000"]
