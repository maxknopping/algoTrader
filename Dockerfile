FROM python:3.6-stretch

RUN pip install -r requirements.txt

ARG APCA_API_SECRET_KEY
ARG APCA_API_KEY_ID
ARG APCA_API_BASE_URL
ENV APCA_API_SECRET_KEY=$APCA_API_SECRET_KEY
ENV APCA_API_KEY_ID=$APCA_API_KEY_ID
ENV APCA_API_BASE_URL=$APCA_API_BASE_URL
ENV PATH=$PATH:$HOME/.local/bin
RUN mkdir /app
COPY . /app
WORKDIR /app
CMD pylivetrader run -f /app/algo.py --backend-config /app/config.json