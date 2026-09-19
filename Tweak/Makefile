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
# Roothide schemes get no libroot from Theos; libroothide supplies jbroot().
# The vendored Roothide Cephei stub already declares an install_name of
# @loader_path/.jbroot/Library/Frameworks/Cephei.framework/Cephei, so the
# framework resolves at runtime without an extra rpath.
$(TWEAK_NAME)_LIBRARIES += roothide
else
# Standard rootless: Theos already injects -lroot, which provides ROOT_PATH_NS.
# Adding it again here would duplicate the link directive.
endif

include $(THEOS_MAKE_PATH)/tweak.mk
