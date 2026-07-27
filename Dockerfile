FROM python:3.11-slim

RUN groupadd --system uygulama_grubu && \
    useradd --system --no-create-home --gid uygulama_grubu uygulama_kullanicisi

ENV HOME=/uygulama

WORKDIR /uygulama

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R uygulama_kullanicisi:uygulama_grubu /uygulama

USER uygulama_kullanicisi

EXPOSE 8000

CMD ["uvicorn", "uygulama.ana:uygulama", "--host", "0.0.0.0", "--port", "8000"]
