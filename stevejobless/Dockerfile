FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY stevejobless ./stevejobless
COPY examples ./examples
RUN pip install --no-cache-dir .
ENV STEVE_DB_URL=sqlite:////data/stevejobless.db
EXPOSE 8787
CMD ["uvicorn", "stevejobless.main:app", "--host", "0.0.0.0", "--port", "8787"]
