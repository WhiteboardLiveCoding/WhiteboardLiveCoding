FROM tiangolo/uwsgi-nginx-flask:python3.6
ARG ARG_BLOB_ACCOUNT
ARG ARG_BLOB_KEY
ARG ARG_HACKER_RANK_KEY

ENV BLOB_ACCOUNT $ARG_BLOB_ACCOUNT
ENV BLOB_KEY $ARG_BLOB_KEY
ENV HACKER_RANK_KEY $ARG_HACKER_RANK_KEY

COPY ./WLC /app/main
COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade -r requirements.txt

# Dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bzip2 \
    ca-certificates \
    curl \
    gcc \
    libc6-dev \
    libgmp-dev \
    libgmp10 \
    make \
    patch \
    zlib1g-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# GHC
RUN mkdir -p /usr/src/ghc
WORKDIR /usr/src/ghc

RUN curl --silent -O https://downloads.haskell.org/~ghc/7.10.1/ghc-7.10.1-x86_64-unknown-linux-deb7.tar.bz2 \
  && echo '3f513c023dc644220ceaba15e5a5089516968b6553b5227e402f079178acba0a  ghc-7.10.1-x86_64-unknown-linux-deb7.tar.bz2' | sha256sum -c - \
  && tar --strip-components=1 -xjf ghc-7.10.1-x86_64-unknown-linux-deb7.tar.bz2 \
  && rm ghc-7.10.1-x86_64-unknown-linux-deb7.tar.bz2 \
  && ./configure \
  && make install \
  && rm -rf /usr/src/ghc \
  && /usr/local/bin/ghc --version

WORKDIR /app
