# 路径兼容性研究记录

标准无根 Theos 使用 `ROOT_PATH_NS`（Objective-C 字符串）和 `ROOT_PATH`（C 字符串）宏，借助 `libroot` 在不同越狱平台解析正确的越狱根路径。标准无根安装前缀为 `/var/jb`，因此任何访问越狱安装区内资源、库或可执行文件的硬编码绝对路径都应通过这些宏解析。

Roothide 官方开发者文档说明：使用文件 API 访问越狱安装区文件时，应使用 Roothide 的 `jbroot` 接口；其 Theos 分支同时兼容使用标准 rootless 路径宏的既有项目。Roothide 包通过 `THEOS_PACKAGE_SCHEME=roothide` 构建。该项目将以 `ROOT_PATH_NS` 处理需要在越狱安装区定位的可执行文件，并保留普通用户偏好设置文件的系统数据路径。

## 来源

1. Theos, [Rootless documentation](https://theos.dev/docs/rootless)
2. Roothide Developer, [update jailbreak apps/tweaks for roothide](https://github.com/roothide/Developer)

Theos 的 `rootless.h` 在 iPhone 目标中包含 `<libroot/libroot.h>`，并将 `ROOT_PATH_NS(nsPath)` 映射为 `JBROOT_PATH_NSSTRING(nsPath)`。因此对 `@"/usr/bin/killall"` 这类位于越狱安装区的 Objective-C 路径，使用 `ROOT_PATH_NS(@"/usr/bin/killall")` 可令 `libroot` 在标准无根与兼容的 Roothide 构建中解析正确前缀；对应的 tweak 目标必须链接 `libroot`。

## arm64e 构建说明

Theos 官方 arm64e 文档指出，iOS 14 起 arm64e ABI 已发生变更；iOS 15–17 属于该较新部署范围。项目将最低 `TARGET` 固定为 iOS 15.0，并同时打包 `arm64` 与 `arm64e` 切片。Linux 版 Theos 的构建规则会显式选择 `libroot_oldabi` 静态库，且本次 Linux 交叉链接器对 `arm64e` 对象输出了 ABI 提示；这不阻止两份 DEB 的签名、通用二进制合并与装包。实际设备启动验证仍应覆盖 A12 及更新芯片。

3. Theos, [arm64e Deployment](https://theos.dev/docs/arm64e-deployment)

## Preferences 崩溃分析（iPhone XS，iOS 15.0）

提交的 IPS 报告来自 `iPhone11,6`（A12、`arm64e`）运行 iOS 15.0。Preferences 主线程因 `EXC_BREAKPOINT/SIGTRAP` 终止，ESR 明确为 pointer-authentication trap；崩溃映像包含 Roothide `libprefs.dylib`。这与偏好设置 bundle 被 `arm64e` Preferences 进程加载的场景相符。

The Apple Wiki 的 Theos 开发参考指出：尽管 arm64e 设备通常可运行 arm64 二进制，PreferenceLoader 通常不能把 arm64 bundle 加载到 arm64e 进程。Theos 官方 arm64e 文档指出 iOS 14 起 arm64e ABI 已变更，且非 macOS 的 Theos 构建规则固定使用旧 ABI。为 iOS 15 的 A12 设备避免旧 ABI 指针认证问题，应改用 macOS/Xcode 12 或更高版本构建最终 `arm64e` Preferences bundle。[3] [4]

4. The Apple Wiki, [Dev:Theos](https://theapplewiki.com/wiki/Dev:Theos)
