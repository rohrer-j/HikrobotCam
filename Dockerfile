# Use Ubuntu as the base image
FROM ubuntu:22.04 as base

# Set working directory to the root of the project
WORKDIR /app

# Copy the SDK zip file into the container
COPY src/MvCamCtrlSDK_STD_V4.4.1_240827.zip /tmp/MvCamCtrlSDK_STD_V4.4.1_240827.zip

# Set environment variables
ENV MVCAM_COMMON_RUNENV=/opt/MVS/lib
# Set the library path
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$MVCAM_COMMON_RUNENV/aarch64

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    unzip wget udev sudo \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install the SDK (the || is used too ognore the errors that occour because the SDK is installed in the container and cannot access some files of the host system)
RUN unzip /tmp/MvCamCtrlSDK_STD_V4.4.1_240827.zip -d /opt/MVS_install && \
    cd /opt/MVS_install && \
    dpkg -i MvCamCtrlSDK_Runtime-4.4.1_aarch64_*.deb || true && \  
    cp -r /opt/MVS_install/* /opt/MVS/ && \
    rm -rf /tmp/MvCamCtrlSDK_STD_V4.4.1_240827.zip /opt/MVS_install


# Copy the requirement folder into the project
COPY requirements.txt /app

#install python packages
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

#protofiles are already needed to build grpc files
COPY protofiles/ /app/protofiles/

#create folder for generated files
RUN mkdir generated

#create grpc files
RUN python3 -m grpc_tools.protoc -I protofiles --python_out=./generated \
           --grpc_python_out=./generated protofiles/hikrobot_cam.proto

#---------------------------Debug stage-----------------------------------
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

#---------------------------production stage-----------------------------------
FROM base as production

# Copy the src folder into the container for the production stage
COPY src/ /app/src  

# Clean up to reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app/src
EXPOSE 50051
ENTRYPOINT [ "python3", "app.py" ]