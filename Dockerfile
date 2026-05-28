FROM python:3.13-slim

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy data files
COPY data/ ./data/

# Copy frontend static files
COPY *.html *.css *.js ./

# Copy modular frontend directories
COPY simulator/ ./simulator/
COPY shared/ ./shared/
COPY components/ ./components/
COPY explorer/ ./explorer/

EXPOSE 8002

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8002"]
