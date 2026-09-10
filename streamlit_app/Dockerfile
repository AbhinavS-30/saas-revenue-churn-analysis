# Optional: containerized local run of the Streamlit page.
# NOTE: the actual free deployment (share.streamlit.io) does NOT use
# this file — Streamlit Community Cloud builds straight from
# requirements.txt. This Dockerfile exists for local reproducibility /
# "runs the same on any machine," matching the rest of this project's
# Docker-for-the-environment approach.
#
# python:3.12-slim is an official multi-arch image (publishes arm64 and
# amd64 under the same tag) — pulls natively on Apple Silicon, no
# emulation, consistent with the Postgres image choice.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# The app reads outputs/summaries/*.json and outputs/figures/*.png from
# the repo — mount or copy the full repo context when building/running,
# not just streamlit_app/. See README "Running the Streamlit app locally".
WORKDIR /app/streamlit_app
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
