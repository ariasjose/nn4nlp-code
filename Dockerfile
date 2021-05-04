ARG VARIANT=3.9
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# Install Java -> OpenJDK-8
# https://api.sdkman.io/2/candidates/java/linux/versions/list?installed=
# ARG JAVA_VERSION=8.0.282-open
# ARG USERNAME=vscode
# ENV SDKMAN_DIR="/usr/local/sdkman"
# COPY .devcontainer/library-scripts/java-debian.sh /tmp/library-scripts/
# RUN bash /tmp/library-scripts/java-debian.sh "${JAVA_VERSION}" "${SDKMAN_DIR}" "${USERNAME}" "true" \
#     && apt-get clean -y \
#     && rm -rf /var/lib/apt/lists/* /tmp/library-scripts

# Create virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

# [Optional] Copy default endpoint specific user settings overrides into container to specify Python path
# COPY .devcontainer/settings.vscode.json /root/.vscode-remote/data/Machine/settings.json
