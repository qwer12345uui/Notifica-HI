# Notifica 1.0.9：iOS 15–17 真机回归测试清单

## 验证范围与当前状态

本版本仅支持 **iOS 15.0–17.x**，并提供两份互斥安装包：标准无根包与 Roothide 隐根包。两包均已完成源码静态检查、交叉编译、DEB 控制字段/安装路径检查、`arm64` 与 `arm64e` 通用二进制检查，以及运行时链接路径检查。标准无根包的载荷位于 `/var/jb`；Roothide 包则由其隐藏根加载器在运行时解析 `.jbroot` 路径。[1] [2]

> **重要说明：** 当前环境没有可连接的已越狱 iPhone/iPad，因此不能将下表中的真机运行结果表述为“已完成”。在至少一台 iOS 15、16、17 设备上完成此清单，并将结果和崩溃日志回传后，才能确认每项 UI 功能均已通过真机回归。

| 项目 | 标准无根 | Roothide 隐根 | 自动化状态 | 真机状态 |
| --- | --- | --- | --- | --- |
| DEB 控制字段与版本 1.0.9 | 已生成 | 已生成 | 已通过 | 待执行 |
| 标准无根 `/var/jb` 前缀 | 已验证 | 不适用 | 已通过 | 待执行 |
| Roothide `.jbroot` 动态路径 | 不适用 | 已验证 | 已通过 | 待执行 |
| `arm64` 与 `arm64e` 切片 | 已验证 | 已验证 | 已通过 | 待执行 |
| 设置页、重启界面、通知 UI | 待设备运行 | 待设备运行 | 不可自动模拟 | 待执行 |

## 安装前检查

请只安装与当前越狱方案一致的一个包。标准无根环境应安装 `Notifica_1.0.9_rootless_iOS15-17.deb`；Roothide 环境应安装 `Notifica_1.0.9_Roothide_iOS15-17.deb`。不要在同一设备上混装两份包，也不要覆盖仍在使用的传统有根 Notifica 安装。

两种方案均要求现有依赖能够满足包控制字段：注入加载器、`org.thebigboss.libcolorpicker (>= 1.6.9)` 与 `ws.hbang.common (>= 1.11)`。先在包管理器中刷新源和依赖，再安装本包。标准无根 Theos 会使用 `libroot` 对越狱安装区路径进行前缀解析；Roothide 版本使用官方 `jbroot` API 和 `libroothide` 运行时路径。[1] [2]

| 环境 | 应安装文件 | 必做的安装后操作 | 不应安装 |
| --- | --- | --- | --- |
| 标准无根 | `Notifica_1.0.9_rootless_iOS15-17.deb` | 在包管理器完成依赖安装后重启界面 | Roothide 包、传统有根包 |
| Roothide 隐根 | `Notifica_1.0.9_Roothide_iOS15-17.deb` | 在 Roothide 对应包管理器完成安装后重启界面 | 标准无根包、传统有根包 |

## 每台设备的回归步骤

在每一个 iOS 大版本至少选一台设备；若可用，iOS 15/16 选择 `arm64` 设备，iOS 16/17 额外选择 A12 或更新的 `arm64e` 设备。`arm64e` 用于带指针认证的系统二进制注入场景，因而应作为此类 tweak 的实际设备覆盖项。[3]

1. 在包管理器安装正确方案的 DEB，确认没有未解决依赖或架构提示。完成后重启界面，并观察 SpringBoard 是否正常返回桌面。
2. 打开“设置 → Notifica”。验证首页、Notifications、Notification Center、Banners、Widgets、Details、Now Playing 与 Experimental 子页均能打开和返回，不出现空白页、闪退或循环重启。
3. 逐项修改一个开关或滑块，返回桌面后使用设置页的 **Respring** 按钮。确认该按钮能够正常重启界面；本版本已将 `killall` 路径改为根据方案解析的越狱安装区路径。
4. 在 Notifications 页面开启通知自定义。分别向至少两个不同应用发送通知，检查圆角、背景、标题、正文、图标显示/隐藏、时间显示/隐藏、颜色和间距等已启用项均生效，并确认禁用开关后恢复系统外观。
5. 在 Banners 页面开启横幅自定义。将设备解锁并触发横幅，检查横幅没有导致 SpringBoard 卡死、黑屏或持续重启。
6. 在 Notification Center 页面启用对应功能，拉下通知中心，测试通知分组、清空、下拉交互、无旧通知提示及打开/关闭多条通知的稳定性。
7. 在 Details 和 Now Playing 页面各启用一项外观选项。展开一条通知详情；同时播放含专辑封面的媒体，检查锁屏/控制中心当前播放区域不会空白或发生重启。
8. 在 Widgets 页面启用项目。若设备系统中仍存在 `WGWidgetPlatterView`，验证旧版 Today widget 显示稳定；若该私有类在该具体系统构建中不存在，本版本会跳过其 hook，而不会为此导致 SpringBoard 崩溃。
9. 在 Experimental 页面分别测试动态颜色和内容着色；再使用 Test Notifications 与 Test Banner 按钮，确认测试通知与横幅均可显示。
10. 保存一套设置、改动多项设置、恢复已保存设置、重命名和删除保存项；最后执行 Reset。每个操作后均重启界面并检查偏好设置是否保留/清空符合预期。

## 日志与失败归档

若应用设置页、通知中心或 SpringBoard 出现崩溃、卡死、循环重启或无效设置，请先停止反复操作，然后收集崩溃报告与安装器日志。应记录：设备型号、芯片架构、精确 iOS 版本、越狱方案与版本、安装的 DEB 文件名、已启用的 Notifica 模块、最后复现步骤，以及崩溃日志中涉及 `Notifica`、`SpringBoard`、`Preferences`、`Cephei`、`libcolorpicker` 或 `libroothide` 的片段。

| 失败现象 | 首要检查 | 应附带信息 |
| --- | --- | --- |
| 安装失败 | 是否选错标准无根/Roothide 包；依赖是否已安装 | 安装器完整错误输出 |
| 设置页闪退 | PreferenceBundles 是否被安装；依赖是否可用 | Preferences 崩溃日志、系统版本 |
| 重启界面后循环重启 | 最近开启的模块和上次设置变更 | SpringBoard 崩溃日志、最后操作 |
| 外观不生效 | Notifica 总开关和子模块开关；是否已重启界面 | 对应页面截图、通知来源应用 |
| Roothide 下加载失败 | 是否误装标准无根包；`libroothide` 依赖 | 包名、动态链接/安装日志 |

## 通过判定

某一方案只有在其对应环境中，完成“安装 → 设置页 → 重启界面 → 通知 → 横幅 → 通知中心 → 当前播放 → 保存/恢复/重置”的全链路回归，且连续数次重启界面后没有崩溃或设置丢失，才标记为真机通过。建议每项重复至少三次，并在每次大版本 iOS 的覆盖设备上保留测试记录。

## References

[1]: https://theos.dev/docs/rootless "Theos Rootless documentation"
[2]: https://github.com/roothide/Developer "Roothide Developer documentation"
[3]: https://theos.dev/docs/arm64e-deployment "Theos arm64e deployment documentation"
