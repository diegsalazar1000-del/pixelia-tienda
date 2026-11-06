# Estudio de anuncios de Pixelia: Python + ffmpeg + poppler + voces Piper (todo local y gratis)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg poppler-utils curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pillow numpy piper-tts
ARG HF=https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX
RUN mkdir -p /voces && cd /voces \
 && curl -fsSL -o es_MX-claude-high.onnx      $HF/claude/high/es_MX-claude-high.onnx \
 && curl -fsSL -o es_MX-claude-high.onnx.json $HF/claude/high/es_MX-claude-high.onnx.json \
 && curl -fsSL -o es_MX-ald-medium.onnx       $HF/ald/medium/es_MX-ald-medium.onnx \
 && curl -fsSL -o es_MX-ald-medium.onnx.json  $HF/ald/medium/es_MX-ald-medium.onnx.json
ENV PIPER_VOICES=/voces PIXELIA_DIR=/pixelia STORE_URL=http://127.0.0.1:3000 PYTHONUNBUFFERED=1
# El código se monta desde /opt/pixelia/estudio: con update.sh basta para actualizarlo.
CMD ["python3", "/pixelia/estudio/estudio.py"]
