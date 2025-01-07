import grpc
import sys
from concurrent import futures
import logging

sys.path.append('/service/generated')
import hikrobot_cam_pb2
import hikrobot_cam_pb2_grpc
from hikrobot import HikRobotCamera, HikRobotCameraException
from ServerLoggerInterceptor import ServerRequestLogger
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound,Internal

class HikRobotCameraServicer(hikrobot_cam_pb2_grpc.HikRobotCameraServiceServicer):
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.camera = HikRobotCamera()

    def Connect(self, request, context):
        try:
            self.camera.connect(request.serial_number)
            return hikrobot_cam_pb2.ConnectResponse(message="Camera connected successfully")
        except HikRobotCameraException as e:
            raise NotFound(f"{request.serial_number} not found")

    def GetImage(self, request, context):
        try:
            img, np_arr = self.camera.getImage()
            image_data = img.tobytes()
            return hikrobot_cam_pb2.GetImageResponse(image_data=image_data, width=img.width, height=img.height)
        except HikRobotCameraException as e:
            raise Internal(str(e))


    def SetExposure(self, request, context):
        try:
            self.camera.setExposure(request.exposure_time_us)
            return hikrobot_cam_pb2.SetExposureResponse()
        except HikRobotCameraException as e:
            raise Internal(str(e))

    def SetGain(self, request, context):
        try:
            self.camera.setGain(request.gain)
            return hikrobot_cam_pb2.SetGainResponse()
        except HikRobotCameraException as e:
            raise Internal(str(e))

    def SetFrameRate(self, request, context):
        try:
            self.camera.setFrameRate(request.frame_rate)
            return hikrobot_cam_pb2.SetFrameRateResponse()
        except HikRobotCameraException as e:
            raise Internal(str(e))

def serve():
    interceptors = [ServerRequestLogger(),ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1),interceptors=interceptors)
    hikrobot_cam_pb2_grpc.add_HikRobotCameraServiceServicer_to_server(HikRobotCameraServicer(), server)
    server.add_insecure_port('[::]:50051')
    logging.info("Server is starting...")
    server.start()
    logging.info("Server started")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
