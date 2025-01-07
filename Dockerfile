# Use Ubuntu as the base image
FROM ubuntu:22.04


# create directory
RUN mkdir /service

# Copy the SDK zip file into the container
COPY HikrobotService/MvCamCtrlSDK_STD_V4.4.1_240827.zip /tmp/MvCamCtrlSDK_STD_V4.4.1_240827.zip

# Set environment variables
ENV MVCAM_COMMON_RUNENV=/opt/MVS/lib

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

# Copy only the requirements file first (this way it will not retrigger pip install if only .py file changes)
COPY HikrobotService/Hikrobot/requirements.txt /service/Hikrobot/requirements.txt

WORKDIR /service/Hikrobot

#install python packages
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# copy the source files
COPY HikrobotService/Hikrobot/ /service/Hikrobot
COPY protobufs/ /service/protobufs    

#create folder for generated files
RUN mkdir generated


#create grpc files
RUN python3 -m grpc_tools.protoc -I ../protobufs --python_out=./generated \
           --grpc_python_out=./generated ../protobufs/hikrobot.proto


# Set the library path
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$MVCAM_COMMON_RUNENV/aarch64

# Clean up to reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/*


EXPOSE 50051
ENTRYPOINT [ "python3", "hikrobot_server.py" ]
