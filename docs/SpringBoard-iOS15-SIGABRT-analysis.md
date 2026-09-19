# SpringBoard SIGABRT (iOS 15.0 / iPhone11,6 / RootHide) — 根因分析

崩溃文件：`SpringBoard-2026-09-20-033909.ips`

## 1. 崩溃概要

| 字段 | 值 |
| --- | --- |
| 进程 | `SpringBoard` (`com.apple.springboard`) |
| 设备 | `iPhone11,6` (iPhone Xs Max, A12) |
| 系统 | iPhone OS 15.0 (19A346) |
| 异常 | `EXC_CRASH` / `SIGABRT`, codes `0x0, 0x0` |
| ASI | `libsystem_c.dylib: abort() called` |
| 崩溃线程 | 0 (`com.apple.main-thread`) |
| Notifica.dylib | `arm64e`, base `0x123524000`, UUID `7c098734-7a4e-3023-8d2d-9f5e9bf6e5ed` |

`lastExceptionBacktrace` 存在, 说明这是**未被捕获的 NSException**, 而不是野指针访问。`abort()` 正是 uncaught exception handler 的收尾动作。

## 2. 回溯解读

`lastExceptionBacktrace` 的 frame 0 是最内层, frame N 由 frame N+1 调用:

```
 0  CoreFoundation        +0x9905c
 1  libobjc.A.dylib       +0x15f54      objc_exception_throw
 2  CoreFoundation        +0x17601c
 3  UIKitCore             +0xf68574
 4  CoreFoundation        +0x2e484
 5  CoreFoundation        +0x2d5c0
 6  Notifica.dylib        +0xAE44       <<< 抛出点
 7  UIKitCore             +0x18dcc8
 8  QuartzCore            +0x3f280      CA::Layer::layout_if_needed
 9  UIKitCore             +0x1f26a0
10+ UserNotificationsUIKit +0x1316c ...  NCNotificationShortLookView 布局
```

即: **UserNotificationsUIKit 的短看通知视图在 layout 过程中, 经 UIKit → QuartzCore → 被 hook 的 `layoutSubviews` 进入 Notifica, Notifica 抛出了异常。**

## 3. 符号化

发布的 dylib 已被 strip, 因此从 deb 中取出 arm64e 切片, 用 capstone 反汇编并重建 `__objc_stubs` → selector 映射 (arm64e 的 `__objc_selrefs` 条目带高位标记 `0x8000000000`, 需按 40 位掩码取值)。

崩溃所在函数 `0xAD30 .. 0xB91C`, 关键片段:

```
0000ad80: mov  x0, x22                 ; self
0000ad84: bl   objc_msgSend(@selector(ntfConfig))
0000ada0: tbz  w0, #0, bail
0000ada8: bl   objc_msgSend(@selector(nextResponder))   x3
0000ae3c: mov  x0, x22                 ; self
0000ae40: bl   objc_msgSend(@selector(_headerContentView))   <<< 抛异常
0000ae44: mov  x29, x29                <<< CRASH (imageOffset 44612)
0000ae48: bl   objc_retainAutoreleasedReturnValue
0000ae60: bl   objc_msgSend(@selector(subviews))
0000ae9c: add  x25, x25, #0xd8b        ; "MTMaterialView"
0000aee4: bl   objc_opt_isKindOfClass
```

该函数引用的 selector 序列精确对应 `Tweak.xm` 中 `%group NotificaNotificationsBanners_iOS13` 的 `%hook NCNotificationShortLookView -layoutSubviews`。

## 4. 根因

`Tweak.h` 的类声明给出了答案:

```objc
@interface MTTitledPlatterView : MTPlatterView {
    UIView* _headerContainerView;
    UIView* _headerOverlayView;
    MTPlatterHeaderContentView* _headerContentView;   // ivar 仍在
    bool _sashHidden;
}

@interface NCNotificationShortLookView : MTTitledPlatterView {
    NCNotificationContentView* _notificationContentView;
    NCNotificationGrabberView* _grabberView;
}
// 没有 -_headerContentView 方法声明
```

**iOS 15 保留了继承自 `MTTitledPlatterView` 的 `_headerContentView` 实例变量, 但删掉了 `-_headerContentView` 这个 getter。**

而崩溃路径用的是选择器调用:

```objc
MTPlatterHeaderContentView *headerContentView = [self _headerContentView];
```

→ `-[NCNotificationShortLookView _headerContentView]: unrecognized selector sent to instance`
→ `NSInvalidArgumentException` → 无人捕获 → `abort()` → SpringBoard 重启。

同一个 hook 中 `ntfColorize` 用的是 `MSHookIvar<MTPlatterHeaderContentView *>(self, "_headerContentView")` (直接读 ivar), 所以那条路径不崩 —— 这也解释了为什么崩溃只发生在 layout 路径。

## 5. 修复要点

1. `ntfHeaderContentViewForView()`: **selector → ivar → 子视图遍历**三级回退。
2. `ntfBackgroundMaterialView()` / `ntfNotificationContentViewForView()` / `ntfViewControllerForAncestor()`: `respondsToSelector:` 守卫; 后者额外带**响应链回退**, 否则该 UIKit 私有方法一改名, 整条通知样式链路会静默失效 (`ntfConfig` 会返回 nil)。
3. `ntfIvarNamed()` 取代 `MSHookIvar<>`: `MSHookIvar` 在 ivar 缺失时对 NULL 解引用, 把「私有细节缺失」变成 `EXC_BAD_ACCESS`。
4. 重复访问提升到局部变量: `layoutSubviews` 每次 SpringBoard 布局都要跑, 原本每个 pass 会执行几十次 `respondsToSelector:` + `performSelector:`。
5. iOS 15 实际生效的 88 个 hook 方法体包 `@try` / `NTF_GUARD`: 残余的私有 API 差异降级为一条日志, 而不是拖垮 SpringBoard。
