# -- coding: utf-8 --

import ctypes
import sys
import threading
import os
import time
import logging
import base64
import io
import numpy as np
from PIL import Image as im
from ctypes import *
sys.path.append(os.path.join(os.path.dirname(__file__),"MvImport"))
sys.path.append("../MvImport")
#from MvImport import MvCameraControl_class
from MvCameraControl_class import *
class HikRobotCameraException(Exception):
    pass

class HikRobotPixelFormat():
	PIXEL_FORMAT_MONO8="Mono8"
	PIXEL_FORMAT_MONO10="Mono10"
	#PIXEL_FORMAT_MONO10PACKED="Mono10Packed" #not implemented yet
	PIXEL_FORMAT_MONO12="Mono12"
	#PIXEL_FORMAT_MONO12PACKED="Mono12Packed" #not implemented yet

class HikRobotCamera():
	g_bExit = False
	cam = None
	logger = None
	nPayloadSize = None
	_IsBusy=False
	_IsInit=False

	def _getImage(self):
		stFrameInfo = MV_FRAME_OUT_INFO_EX()
		if self._triggerModeActive:
			self.triggerNewPicture()
		if self._currentPixelformat==HikRobotPixelFormat.PIXEL_FORMAT_MONO8:
			data_buf = (c_ubyte* int(self.nPayloadSize))()
		else:
			data_buf = (2*c_ubyte* int(self.nPayloadSize))()
		memset(byref(stFrameInfo), 0, sizeof(stFrameInfo))
		ret = self.cam.MV_CC_GetOneFrameTimeout(byref(data_buf), self.nPayloadSize, stFrameInfo, 1000)
		return stFrameInfo, data_buf, ret

	def getImage(self):
		""" 
		Read image from camera.
		
		:returns: Image from camera.
		:rtype: Image, numpy array
		"""
		stFrameInfo, data_buf, ret = self._getImage()
		if ret == 0:
			self.logger.info("get one frame: Width[%d], Height[%d], PixelType[0x%x], nFrameNum[%d]"  % (stFrameInfo.nWidth, stFrameInfo.nHeight, stFrameInfo.enPixelType,stFrameInfo.nFrameNum))
			if self._currentPixelformat==HikRobotPixelFormat.PIXEL_FORMAT_MONO8:
				np_arr = np.ctypeslib.as_array(data_buf)
				np_arr = np.reshape(np_arr, (stFrameInfo.nHeight, stFrameInfo.nWidth))
				img = im.fromarray(np_arr, 'L')
			else:
				pdata_as16 = ctypes.cast(data_buf,ctypes.POINTER(ctypes.c_ushort))
				np_arr = np.ctypeslib.as_array(pdata_as16,(stFrameInfo.nHeight,stFrameInfo.nWidth))
				img = im.fromarray(np_arr, 'I;16')
			return img, np_arr
		else:
			self.logger.error("no data[0x%x]" % ret)
			raise HikRobotCameraException("no data[0x%x]" % ret)
		
	def connect(self, serialNumber):
		""" 
		Connect the camera by serial number
		
		:returns: None
		:rtype: None
		"""
		if self._IsInit==True:
			self.disconnect()
		self.logger = logging.getLogger(__name__)
		logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
		# Get SDK Version
		SDKVersion = MvCamera.MV_CC_GetSDKVersion()
		self.logger.info("SDKVersion[0x%x]" % SDKVersion)

		deviceList = MV_CC_DEVICE_INFO_LIST()
		tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE

		# ch:枚举设备 | en:Enum device
		ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
		if ret != 0:
			self.logger.error("enum devices fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("num devices fail! ret[0x%x]" % ret)

		if deviceList.nDeviceNum == 0:
			self.logger.error("camera device found")
			raise HikRobotCameraException("No camera device found")

		#Connect do according serial number
		index=-1
		for i in range(0, deviceList.nDeviceNum):
			mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
			if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
				self.logger.info("\ngige device: [%d]" % i)
				strModeName = ""
				for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName:
					strModeName = strModeName + chr(per)
				self.logger.info("device model name: %s" % strModeName)

				nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
				nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
				nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
				nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
				self.logger.info("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
			elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
				self.logger.info("\nu3v device: [%d]" % i)
				strModeName = ""
				for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName:
					if per == 0:
						break
					strModeName = strModeName + chr(per)
				self.logger.info("device model name: %s" % strModeName)

				strSerialNumber = ""
				for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber:
					if per == 0:
						break
					strSerialNumber = strSerialNumber + chr(per)
				self.logger.info("user serial number: %s" % strSerialNumber)
				if serialNumber==strSerialNumber:
					index=i
					break

		if index==-1:
			self.logger.error("Serial %s not found" % serialNumber)
			raise HikRobotCameraException("Serial %s not found" % serialNumber)
		# ch:创建相机实例 | en:Creat Camera Object
		self.cam = MvCamera()
		
		# ch:选择设备并创建句柄| en:Select device and create handle
		stDeviceList = cast(deviceList.pDeviceInfo[int(index)], POINTER(MV_CC_DEVICE_INFO)).contents

		ret = self.cam.MV_CC_CreateHandle(stDeviceList)
		if ret != 0:
			self.logger.error("create handle fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("create handle fail! ret[0x%x]" % ret)

		# ch:打开设备 | en:Open device
		ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
		if ret != 0:
			self.logger.error(f"open device %x fail! ret[0x%x]" % index, ret)
			raise HikRobotCameraException("open device fail! ret[0x%x]" % ret)
		self.logger.info("Camera successfully opend")
		
		# ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
		if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
			nPacketSize = self.cam.MV_CC_GetOptimalPacketSize()
			if int(nPacketSize) > 0:
				ret = self.cam.MV_CC_SetIntValue("GevSCPSPacketSize",nPacketSize)
				if ret != 0:
					self.logger.warn("Set Packet Size fail! ret[0x%x]" % ret)
			else:
				self.logger.warn("Get Packet Size fail! ret[0x%x]" % nPacketSize)	

		# ch:获取数据包大小 | en:Get payload size
		stParam =  MVCC_INTVALUE()
		memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))
		
		ret = self.cam.MV_CC_GetIntValue("PayloadSize", stParam)
		if ret != 0:
			self.logger.error("get payload size fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("get payload size fail! ret[0x%x]" % ret)
		self.nPayloadSize = stParam.nCurValue

		#standard settings
		self.setSoftwareTriggerMode()	
		# ch:开始取流 | en:Start grab image
		ret = self.cam.MV_CC_StartGrabbing()
		if ret != 0:
			self.logger.error("start grabbing fail! ret[0x%x]" % ret)
			sys.exit()
		self.logger.info("Grabbing started, camera is fully initialized")

		self.setPixelFormat(HikRobotPixelFormat.PIXEL_FORMAT_MONO8)
		#get one image to clear buffer
		self._getImage()
		self._IsInit=True

	def setExposure(self, exposureTime_us):
		""" 
		Set Exposure time in us
		
		:returns: None
		:rtype: None
		"""
		ret=self.cam.MV_CC_SetFloatValue("ExposureTime", exposureTime_us)
		if ret != 0:
			self.logger.error("set exposure time fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set exposure time fail! ret[0x%x]" % ret)
	def setGain(self, gain):
		""" 
		Set Gain (function not tested)
		
		:returns: None
		:rtype: None
		"""
		ret=self.cam.MV_CC_SetFloatValue("Gain", gain)
		if ret != 0:
			self.logger.error("set gain time fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set gain time fail! ret[0x%x]" % ret)
	def setFrameRate(self, AcquisitionFrameRate):
		""" 
		Set Frame Rate for continuous mode
		
		:returns: None
		:rtype: None
		"""
		ret=self.cam.MV_CC_SetFloatValue("AcquisitionFrameRate", AcquisitionFrameRate)
		if ret != 0:
			self.logger.error("set gacquistion frame fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set acquistion frame time fail! ret[0x%x]" % ret)
	def setSoftwareTriggerMode(self):
		""" 
		Turn on software trigger
		
		:returns: None
		:rtype: None
		"""
		#Set trigger mode ON
		ret = self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_ON)
		if ret != 0:
			self.logger.error("set trigger mode fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set trigger mode fail! ret[0x%x]" % ret)

		#Set software trigger
		ret = self.cam.MV_CC_SetEnumValue("TriggerSource", MV_TRIGGER_SOURCE_SOFTWARE)
		if ret != 0:
			self.logger.error("set trigger source fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set trigger mode fail! ret[0x%x]" % ret)
		self._triggerModeActive=True

	def setContinuousMode(self,framerate):
		""" 
		Set Continuos Mode (turn trigger mode off)
		
		:returns: None
		:rtype: None
		"""
		# ch:设置触发模式为off | en:Set trigger mode as off
		ret = self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
		if ret != 0:
			self.logger.error("set trigger mode fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("set trigger mode fail! ret[0x%x]" % ret)
		self.setFrameRate(framerate)
		self._triggerModeActive=False

	def triggerNewPicture(self):
		""" 
		Activate software trigger to aquire new image
		
		:returns: None
		:rtype: None
		"""
		if self._triggerModeActive:
			#set software trigger
			ret=self.cam.MV_CC_SetCommandValue("TriggerSoftware")
			if ret != 0:
				self.logger.error("TriggerSoftware failed ret:[0x%x]" % ret)
				raise HikRobotCameraException("TriggerSoftware failed ret:[0x%x]" % ret)
		else:
			self.logger.warning("Trigger Mode is not enabled, softwareTrigger has no effect")

	def setPixelFormat(self,Format:HikRobotPixelFormat):
		""" 
		Change pixel format (attention not all format are implemented yet)
		
		:returns: None
		:rtype: None
		"""
		# ch:停止取流 | en:Stop grab image
		ret = self.cam.MV_CC_StopGrabbing()
		if ret != 0:
			self.logger.error("stop grabbing fail! ret[0x%x]" % ret)
			del data_buf
			raise HikRobotCameraException("stop grabbing fail! ret[0x%x]" % ret)

		ret= self.cam.MV_CC_SetEnumValueByString("PixelFormat",Format)
		if ret != 0:
				self.logger.error("TriggerSoftware failed ret:[0x%x]" % ret)
				raise HikRobotCameraException("TriggerSoftware failed ret:[0x%x]" % ret)
		self._currentPixelformat=Format
		
		# ch:开始取流 | en:Start grab image
		ret = self.cam.MV_CC_StartGrabbing()
		if ret != 0:
			self.logger.error("start grabbing fail! ret[0x%x]" % ret)
			sys.exit()
		self.logger.info("Grabbing started, camera is fully initialized")

				# ch:获取数据包大小 | en:Get payload size
		stParam =  MVCC_INTVALUE()
		memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))
		
		ret = self.cam.MV_CC_GetIntValue("PayloadSize", stParam)
		if ret != 0:
			self.logger.error("get payload size fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("get payload size fail! ret[0x%x]" % ret)
		self.nPayloadSize = stParam.nCurValue


	def disconnect(self):
		""" 
		Disconnect camera
		
		:returns: None
		:rtype: None
		"""
		# ch:停止取流 | en:Stop grab image
		ret = self.cam.MV_CC_StopGrabbing()
		if ret != 0:
			self.logger.error("stop grabbing fail! ret[0x%x]" % ret)
			del data_buf
			raise HikRobotCameraException("stop grabbing fail! ret[0x%x]" % ret)

		# ch:关闭设备 | Close device
		ret = self.cam.MV_CC_CloseDevice()
		if ret != 0:
			self.logger.error("close deivce fail! ret[0x%x]" % ret)
			del data_buf
			raise HikRobotCameraException("close deivce fail! ret[0x%x]" % ret)

		# ch:销毁句柄 | Destroy handle
		ret = self.cam.MV_CC_DestroyHandle()
		if ret != 0:
			self.logger.error("destroy handle fail! ret[0x%x]" % ret)
			raise HikRobotCameraException("destroy handle fail! ret[0x%x]" % ret)
		self._IsInit=False
		


if __name__ == '__main__':
	cam = HikRobotCamera()
	cam.connect("J84088695")
	cam.setExposure(100000)
	cam.setPixelFormat(HikRobotPixelFormat.PIXEL_FORMAT_MONO12)
	img=cam.getImage()[0]
	img.save("test16.tif")
	cam.setPixelFormat(HikRobotPixelFormat.PIXEL_FORMAT_MONO8)
	img=cam.getImage()[0]
	img.save("test8.tif")
	#cam.setContinuousMode(10)
	#time.sleep(5)
	#cam.getImage()
	cam.disconnect()
