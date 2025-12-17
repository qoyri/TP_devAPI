FROM mysql:8.0

RUN microdnf install -y wget unzip && microdnf clean all

COPY init.sh /init.sh
RUN chmod +x /init.sh

ENTRYPOINT ["/init.sh"]
