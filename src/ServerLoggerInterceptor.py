from grpc_interceptor import ServerInterceptor
import logging
_logger = logging.getLogger('grpcLogger')
class ServerRequestLogger(ServerInterceptor):
    def intercept(self, method, request, context, method_name):
        try:
            _logger.info(f"Received Request {method_name=},{request=}")
            response= method(request, context)
            #here we could log the response
            # _logger.info(f"Sending response from method: {method.__name__}, Response: {response}")
            return response
        except Exception as e:
            self.log_error(e,method_name)
            raise

    def log_error(self, e: Exception, method_name) -> None:
        #_logger.error(f"Error occurred in method '{method_name}': {str(e)}")
        pass #not needed to log the error as it is logged by the grpc framework already. Could be used to log somewhere else

    