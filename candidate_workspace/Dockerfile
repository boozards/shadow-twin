# Candidate Cloud Run Microservice
# Python 3.12 + FastAPI + Pydantic v2 + asyncpg
FROM python:3.12-slim

WORKDIR /app

# Optimize layer caching for sub-3-second rebuilds in the Critic loop
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/candidate_workspace/
ENV PYTHONPATH=/app

EXPOSE 8080
CMD ["uvicorn", "candidate_workspace.app:app", "--host", "0.0.0.0", "--port", "8080"]
