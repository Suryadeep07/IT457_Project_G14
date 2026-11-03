# Start from a small official Python image
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Install the libraries first so Docker can reuse this step
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Do not run as the root user
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
# gunicorn is the production web server [CORRECTED]; (OLD: 2 workers because the instance has 2 vCPUs)
CMD ["gunicorn", "-w", "2", "--threads", "4", "-b", "0.0.0.0:8000", "--timeout", "30", "app:app"]