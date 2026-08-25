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
# Cephei 2 exports C++ `using` aliases through its module header on current Xcode.
ADDITIONAL_OBJCFLAGS = -fobjc-arc -Wno-deprecated-declarations -std=c++14

ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
# Roothide resolves rootless path macros through libroothide and needs this
# rpath to locate Cephei below the hidden jailbreak root.
$(TWEAK_NAME)_LIBRARIES += roothide
ADDITIONAL_LDFLAGS += -rpath '@loader_path/.jbroot/Library/Frameworks'
else
# Standard rootless uses libroot for ROOT_PATH_NS and related macros.
$(TWEAK_NAME)_LIBRARIES += root
endif

include $(THEOS_MAKE_PATH)/tweak.mk
