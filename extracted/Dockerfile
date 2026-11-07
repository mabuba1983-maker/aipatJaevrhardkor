FROM python:3.11-slim
WORKDIR /app
COPY . .
# 1 = install PyTorch (CPU) so a trained model.pt can be served; 0 = knowledge-base only (small image)
RUN pip install --no-cache-dir numpy
ARG WITH_TORCH=0
RUN if [ "$WITH_TORCH" = "1" ]; then pip install --no-cache-dir numpy torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple; fi
ENV NUWAA_PORT=8000
EXPOSE 8000
CMD ["python", "server/server.py"]
