FROM prefecthq/prefect:3.6.10-python3.12

# Install prefect-kubernetes
RUN pip install --no-cache-dir prefect-kubernetes==0.7.2

# Copy your flow code
WORKDIR /opt/prefect/flows
COPY . /opt/prefect/flows

# Set entrypoint for Prefect
ENTRYPOINT ["python", "-m", "prefect"]
