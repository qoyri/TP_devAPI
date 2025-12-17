# build with sbt (JDK + sbt)
FROM sbtscala/scala-sbt:eclipse-temurin-17.0.15_6_1.11.7_2.12.20 AS build
WORKDIR /app

# copy project descriptor first for layer caching
COPY project ./project
COPY build.sbt ./

# fetch deps and compile
RUN sbt -batch update compile

# copy full sources and produce normal package (no assembly/fat-jar)
COPY src ./src
RUN sbt -batch package

# collect the packaged project jar(s) and all runtime dependency jars into /app/lib
RUN mkdir -p /app/lib && \
    cp target/scala-*/*.jar /app/lib/ 2>/dev/null || true && \
    sbt -batch "show runtime:fullClasspath" \
      | perl -nle 'print $1 if /\(([^)]+\.jar)\)/' \
      | while read jar; do cp -n "$jar" /app/lib/ 2>/dev/null || true; done

# run image (JRE only)
FROM eclipse-temurin:17-jre-jammy AS run
WORKDIR /app
COPY --from=build /app/lib /app/lib

ENV APP_MAIN="siren.analyticcli"
EXPOSE 15002

CMD ["sh", "-c", "exec java \
  --add-exports=java.base/sun.nio.ch=ALL-UNNAMED \
  --add-opens=java.base/java.nio=ALL-UNNAMED \
  --add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
  -cp '/app/lib/*' ${APP_MAIN}"]
