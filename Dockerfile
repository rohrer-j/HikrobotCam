# Use Ubuntu as the base image
FROM python as base

# Set working directory to the root of the project
WORKDIR /app

# Copy the requirement folder into the project
COPY requirements.txt /app

# Install python packages
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# protofiles are already needed to build grpc files
COPY protofiles/ /app/protofiles/

# Create folder for generated files
RUN mkdir generated

# Create grpc files
RUN python3 -m grpc_tools.protoc -I protofiles --python_out=./generated \
--grpc_python_out=./generated protofiles/hikrobot_cam.proto

# Set environment variables
ENV MVCAM_COMMON_RUNENV=/opt/MVS/lib
# Set the library path
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$MVCAM_COMMON_RUNENV/aarch64

# End of base steps

#---------------------------Debug stage--------------
FROM base as debug

# Install debugpy (Python debugger for remote debugging)
RUN python3 -m pip install debugpy

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# Expose the port for debugging
EXPOSE 5678
WORKDIR /app/src
EXPOSE 50051


#---------------------------Production stage------------
FROM base as production

# Copy the src folder into the container for the production stage
COPY src/ /app/src

# Clean up to reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app/src
EXPOSE 50051
ENTRYPOINT [ "python3", "app.py" ]