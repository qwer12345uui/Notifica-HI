ARCHS = arm64 arm64e
TARGET = iphone:clang:latest:15.0

INSTALL_TARGET_PROCESSES = SpringBoard

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = Notifica
$(TWEAK_NAME)_FILES = Tweak.xm NTFConfig.m NTFManager.m NEPColor.m NEPColorUtils.m NEPPalette.m
$(TWEAK_NAME)_FRAMEWORKS += QuartzCore MediaPlayer
$(TWEAK_NAME)_LIBRARIES += colorpicker
$(TWEAK_NAME)_EXTRA_FRAMEWORKS += Cephei
$(TWEAK_NAME)_PRIVATE_FRAMEWORKS += MediaRemote
ADDITIONAL_OBJCFLAGS = -fobjc-arc -Wno-deprecated-declarations
# Cephei 2.0's generated Swift compatibility header uses C++11 aliases; Tweak.xm is Objective-C++.
ADDITIONAL_OBJCCFLAGS = -std=c++11

ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
ADDITIONAL_LDFLAGS += -rpath '@loader_path/.jbroot/Library/Frameworks'
endif

include $(THEOS_MAKE_PATH)/tweak.mk
