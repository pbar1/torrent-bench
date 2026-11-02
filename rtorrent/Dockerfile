# The upstream project does not publish an official image. Build its stable
# release and matching Rakshasa libtorrent without patches or a web UI bundle.
FROM alpine@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a AS build
COPY apk-build.lock /apk-build.lock
RUN apk add --no-cache $(cat /apk-build.lock)
WORKDIR /src
ADD https://github.com/rakshasa/rtorrent/releases/download/v0.16.27/libtorrent-0.16.27.tar.gz libtorrent.tar.gz
ADD https://github.com/rakshasa/rtorrent/releases/download/v0.16.27/rtorrent-0.16.27.tar.gz rtorrent.tar.gz
RUN echo 'b7ee3f637da6d136fb70a4566fbea8e444f7a2e259596e8612adeb0c7c520fd1  libtorrent.tar.gz' | sha256sum -c - \
 && echo '645e5ea863fee2c3a0f745be6235a37e80cf7db6a07bc82ca31d49bf65f2a52a  rtorrent.tar.gz' | sha256sum -c - \
 && tar xzf libtorrent.tar.gz && tar xzf rtorrent.tar.gz
RUN cd libtorrent-0.16.27 && ./configure --prefix=/usr --disable-debug \
 && make -j4 && make install DESTDIR=/out
RUN cd rtorrent-0.16.27 && PKG_CONFIG_PATH=/out/usr/lib/pkgconfig \
    CPPFLAGS=-I/out/usr/include LDFLAGS=-L/out/usr/lib \
    ./configure --prefix=/usr --disable-debug --with-xmlrpc-tinyxml2 \
 && make -j4 && make install DESTDIR=/out
RUN apk info -v > /out/build-packages.txt

FROM alpine@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a
COPY apk-runtime.lock /apk-runtime.lock
RUN apk add --no-cache $(cat /apk-runtime.lock)
COPY --from=build /out/ /
CMD ["rtorrent", "-n", "-o", "import=/config/rtorrent.rc"]
