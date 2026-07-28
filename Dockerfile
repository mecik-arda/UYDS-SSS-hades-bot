FROM python:3.11-slim

RUN groupadd --system uygulama_grubu && \
    useradd --system --no-create-home --gid uygulama_grubu uygulama_kullanicisi

ENV HOME=/uygulama
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /uygulama

COPY requirements.txt .

RUN pip install --no-cache-dir pip==26.1.2 setuptools==83.0.0

RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.13.0+cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=uygulama_kullanicisi:uygulama_grubu . .

ENV HOME=/tmp

USER uygulama_kullanicisi

EXPOSE 8000

CMD ["uvicorn", "uygulama.ana:uygulama", "--host", "0.0.0.0", "--port", "8000"]
