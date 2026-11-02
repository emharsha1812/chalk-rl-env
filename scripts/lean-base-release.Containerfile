# Add the upstream notices and source information to the separately built base.
FROM chalk-fineenvs-lean-base:d7056fd
ARG CHALK_SOURCE
ARG CHALK_REVISION
LABEL org.opencontainers.image.source=$CHALK_SOURCE \
      org.opencontainers.image.revision=$CHALK_REVISION \
      org.opencontainers.image.description="Lean base for Chalk's experimental FineEnvs math task"
COPY third_party/openai_math/ /usr/share/licenses/chalk-openai-math/
COPY third_party_licenses/ /usr/share/licenses/chalk-lean-tools/
