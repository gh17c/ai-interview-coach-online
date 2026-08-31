FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app.py app_ui.py app_ui.css .env.example ./
COPY modules ./modules
COPY components ./components
COPY .streamlit ./.streamlit
RUN mkdir -p /app/data/sessions

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"

CMD ["sh", "-c", "streamlit run app_ui.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
