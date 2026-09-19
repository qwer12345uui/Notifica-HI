#!/usr/bin/env python3
"""Apply the iOS 15 private-API hardening pass to Tweak/Tweak.xm.

Why this exists
---------------
SpringBoard-2026-09-20-033909.ips (iPhone11,6 / iOS 15.0 / RootHide) reports
EXC_CRASH (SIGABRT) on the main thread with "abort() called". Its last
exception backtrace frames are:

    5  CoreFoundation
    6  Notifica.dylib  +0xAE44     <- throw site
    7  UIKitCore
    8  QuartzCore
   10+ UserNotificationsUIKit      <- NCNotificationShortLookView layout

Disassembling the stripped arm64e slice at +0xAE44 gives:

    mov  x0, x22
    bl   objc_msgSend(@selector(_headerContentView))   <- throws

inside the hooked -[NCNotificationShortLookView layoutSubviews].

Tweak.h shows why. NCNotificationShortLookView derives from
MTTitledPlatterView, which still declares the `_headerContentView` *ivar*,
but iOS 15 no longer exposes the `-_headerContentView` *accessor*. The message
therefore raises NSInvalidArgumentException and, because nothing catches it,
SpringBoard aborts in the middle of its layout pass.

Note that the same hook reads the same view through
MSHookIvar<MTPlatterHeaderContentView *>(self, "_headerContentView") in
-ntfColorize; that path reads the ivar directly and never crashes, which is
exactly why only the layout path dies.

What this pass does
-------------------
1. ntfHeaderContentViewForView(): selector -> ivar -> subview walk.
2. ntfBackgroundMaterialView(), ntfNotificationContentViewForView(),
   ntfViewControllerForAncestor(): respondsToSelector-guarded lookups, the
   last one with a responder-chain fallback so a renamed UIKit helper cannot
   silently disable every notification style (ntfConfig would return nil).
3. ntfIvarNamed() replaces MSHookIvar<>, which dereferences NULL when an ivar
   is missing and turns a missing private detail into EXC_BAD_ACCESS.
4. Repeated accessors are hoisted into locals: layoutSubviews runs on every
   SpringBoard layout pass, and the naive rewrite performed dozens of
   respondsToSelector:+performSelector: calls per pass.
5. The hook bodies that iOS 15 actually initialises are wrapped in
   @try / NTF_GUARD so any residual private-API mismatch degrades to a logged
   no-op instead of taking SpringBoard down.

The pass is idempotent: once Tweak.xm carries NTF_GUARD it exits without
touching the file, so it is safe to keep as a build step.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "Tweak", "Tweak.xm")

HELPERS = r'''
/* -------------------------------------------------------------------------
   iOS 15 private-API resilience
   -------------------------------------------------------------------------
   Notifica's iOS 13 code paths still call accessors that iOS 15 dropped.
   SpringBoard-2026-09-20-033909.ips is the canonical example: the hooked
   -[NCNotificationShortLookView layoutSubviews] sent `_headerContentView`,
   which no longer exists as a method on iOS 15 (the ivar survived on
   MTTitledPlatterView, the accessor did not). The resulting
   NSInvalidArgumentException was uncaught and SpringBoard aborted with
   SIGABRT inside its layout pass.

   Every private accessor below is therefore resolved defensively: try the
   selector, fall back to the ivar, fall back to a subview walk, and give up
   with nil rather than raising. ------------------------------------------*/

/* object_getIvar() guarded by an ivar lookup that walks the superclass chain.
   MSHookIvar<> is not usable here: it dereferences NULL when the ivar is
   missing, which turns a missing private detail into EXC_BAD_ACCESS. */
static id ntfIvarNamed(id object, const char *name) {
    if (!object || !name) return nil;
    Ivar ivar = class_getInstanceVariable([object class], name);
    if (!ivar) return nil;
    @try {
        id value = object_getIvar(object, ivar);
        return value;
    } @catch (NSException *exception) {
        return nil;
    }
}

/* -performSelector: guarded by -respondsToSelector:, so a selector that a
   newer UIKit removed simply yields nil instead of raising. */
static id ntfPerformIfAvailable(id target, SEL selector) {
    if (!target || !selector) return nil;
    if (![target respondsToSelector:selector]) return nil;
    @try {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Warc-performSelector-leaks"
        return [target performSelector:selector];
#pragma clang diagnostic pop
    } @catch (NSException *exception) {
        return nil;
    }
}

/* The platter header. iOS 12 exposed -_headerContentView; iOS 13-14 kept both
   the accessor and the ivar; iOS 15 kept only the ivar on MTTitledPlatterView.
   Try all three before giving up. */
static MTPlatterHeaderContentView *ntfHeaderContentViewForView(UIView *view) {
    if (!view) return nil;

    static Class mtHeaderClass = nil;
    static Class plHeaderClass = nil;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        mtHeaderClass = NSClassFromString(@"MTPlatterHeaderContentView");
        plHeaderClass = NSClassFromString(@"PLPlatterHeaderContentView");
    });

    id hcv = ntfPerformIfAvailable(view, @selector(_headerContentView));
    if (hcv) return (MTPlatterHeaderContentView *)hcv;

    hcv = ntfIvarNamed(view, "_headerContentView");
    if (hcv) return (MTPlatterHeaderContentView *)hcv;

    // Last resort: the header is a subview of the platter on every known
    // layout, so a shallow walk recovers it even if both names change again.
    for (UIView *subview in view.subviews) {
        if ((mtHeaderClass && [subview isKindOfClass:mtHeaderClass]) ||
            (plHeaderClass && [subview isKindOfClass:plHeaderClass])) {
            return (MTPlatterHeaderContentView *)subview;
        }
    }
    for (UIView *subview in view.subviews) {
        for (UIView *nested in subview.subviews) {
            if ((mtHeaderClass && [nested isKindOfClass:mtHeaderClass]) ||
                (plHeaderClass && [nested isKindOfClass:plHeaderClass])) {
                return (MTPlatterHeaderContentView *)nested;
            }
        }
    }
    return nil;
}

static MTMaterialView *ntfBackgroundMaterialView(UIView *view) {
    return (MTMaterialView *)ntfPerformIfAvailable(view, @selector(backgroundMaterialView));
}

static NCNotificationContentView *ntfNotificationContentViewForView(UIView *view) {
    id ncv = ntfPerformIfAvailable(view, @selector(_notificationContentView));
    if (ncv) return (NCNotificationContentView *)ncv;
    return (NCNotificationContentView *)ntfIvarNamed(view, "_notificationContentView");
}

/* Returns id on purpose: callers ask for -delegate, which UIViewController
   does not declare, and the compiler rejects that through a typed receiver. */
static id ntfViewControllerForAncestor(UIView *view) {
    id controller = ntfPerformIfAvailable(view, @selector(_viewControllerForAncestor));
    if (controller) return controller;

    /* -ntfConfig keys off this controller, so returning nil here would
       silently disable every notification style. Walk the responder chain
       instead of giving up: the owning controller is always on it. */
    for (UIResponder *responder = view; responder; responder = responder.nextResponder) {
        if ([responder isKindOfClass:[UIViewController class]]) return responder;
    }
    return nil;
}

/* Wraps a hook body so that a residual private-API mismatch degrades to a
   logged no-op instead of taking SpringBoard down. */
#define NTF_GUARD(context) \
    @catch (NSException *exception) { \
        NSLog(@"[Notifica] %@ suppressed %@: %@", (context), exception.name, exception.reason); \
    }
'''

ANCHOR = '''void ntfSetIconForHCV(MTPlatterHeaderContentView* hcv, UIImage *icon) {
    if (!hcv) return;

    if ([hcv respondsToSelector:@selector(setIcon:)]) {
        [hcv setIcon:icon];
    } else if ([hcv respondsToSelector:@selector(setIcons:)]) {
        [hcv setIcons:@[icon]];
    }
}'''

# Hook bodies that the iOS 15 branch of %ctor actually initialises.
HOOKS = [
    'MTMaterialView', 'PLPlatterHeaderContentView', 'MTPlatterHeaderContentView',
    'NCNotificationShortLookViewController', 'NCNotificationViewControllerView',
    'NCNotificationListCell', 'NCNotificationListCellActionButtonsView',
    'NCNotificationListCoalescingHeaderCell', 'NCNotificationListCollectionView',
    'NCNotificationListCache', 'NCNotificationShortLookView',
    'NCNotificationLongLookView', 'SBMediaController',
    'SBDashBoardAdjunctItemView', 'WGWidgetPlatterView',
    'NCNotificationListCollectionViewFlowLayout',
    'NCNotificationListSectionRevealHintView', 'CSCombinedListViewController',
    'SBCoverSheetPrimarySlidingViewController',
    'NCNotificationStructuredListViewController',
    'SBDashBoardIdleTimerProvider',
]


def brace_depth(lines):
    """Brace depth at the end of each line, ignoring literal contents."""
    out, d = [], 0
    for ln in lines:
        s = re.sub(r'@"(\\.|[^"\\])*"', '@""', ln)
        s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
        s = re.sub(r'//.*$', '', s)
        for ch in s:
            if ch == '{':
                d += 1
            elif ch == '}':
                d -= 1
        out.append(d)
    return out


def method_bounds(depth, i):
    start = None
    j = i
    while j >= 0:
        if depth[j] == 1 and (j == 0 or depth[j - 1] == 0):
            start = j
            break
        j -= 1
    if start is None:
        return None
    end = len(depth) - 1
    for j in range(i, len(depth)):
        if depth[j] == 0:
            end = j
            break
    return start, end


def hoist_accessors(lines):
    """Hoist repeated defensive-accessor calls into a local per method."""
    depth = brace_depth(lines)
    targets = [
        ('ntfBackgroundMaterialView(self)',
         'MTMaterialView *backgroundMaterialView', 'backgroundMaterialView'),
        ('ntfNotificationContentViewForView(self)',
         'NCNotificationContentView *notificationContentView', 'notificationContentView'),
        ('ntfViewControllerForAncestor(self)',
         'id viewControllerForAncestor', 'viewControllerForAncestor'),
    ]
    inserts, replacements = [], []
    for call, decl, var in targets:
        by_method = {}
        for i, l in enumerate(lines):
            if call in l:
                b = method_bounds(depth, i)
                if b:
                    by_method.setdefault(b, []).append(i)
        for (start, end), occ in by_method.items():
            decl_re = re.compile(r'\b%s\s*=\s*%s' % (re.escape(var), re.escape(call)))
            has_decl = decl_re.search('\n'.join(lines[start:end + 1])) is not None
            for i in occ:
                if has_decl and decl_re.search(lines[i]):
                    continue  # keep the initialiser intact
                replacements.append((i, call, var))
            if has_decl:
                continue
            # Insert after %orig when present: reading a private subview
            # before the original implementation runs can legitimately
            # return nil on a not-yet-laid-out platter.
            ins_at = start
            for k in range(start + 1, min(end, start + 10) + 1):
                if '%orig' in lines[k]:
                    ins_at = k
                    break
            indent = re.match(r'\s*', lines[ins_at]).group(0) or '    '
            inserts.append((ins_at, '%s%s = %s;' % (indent, decl, call)))

    for i, call, var in replacements:
        lines[i] = lines[i].replace(call, var)
    # Descending order keeps the collected indices valid.
    for start, text in sorted(inserts, key=lambda x: -x[0]):
        lines.insert(start + 1, text)
    return len(inserts), len(replacements)


def guard_hook_bodies(lines):
    """Wrap iOS 15 hook bodies in @try / NTF_GUARD."""
    depth = brace_depth(lines)
    blocks = []
    i = 0
    while i < len(lines):
        m = re.match(r'^%hook\s+(\w+)\s*$', lines[i].strip())
        if m and m.group(1) in HOOKS:
            j = i + 1
            while j < len(lines) and lines[j].strip() != '%end':
                j += 1
            blocks.append((m.group(1), i, j))
            i = j
        i += 1

    edits = []
    for cls, bstart, bend in blocks:
        for k in range(bstart, bend):
            stripped = lines[k].strip()
            if not re.match(r'^[-+]\s*\(', stripped):
                continue
            if not lines[k].rstrip().endswith('{'):
                continue
            if depth[k] != 1:
                continue
            end = k + 1
            while end < len(lines) and depth[end] != 0:
                end += 1
            if end >= len(lines):
                continue
            indent = re.match(r'\s*', lines[k]).group(0)
            sel = re.sub(r'^[-+]\s*', '', stripped.split('{')[0].strip()) or 'method'
            edits.append((k, 'after', '%s@try {' % indent))
            edits.append((end, 'before', '%s} NTF_GUARD(@"-[%s %s]")' % (indent, cls, sel)))

    for idx, pos, text in sorted(edits, key=lambda x: (-x[0], x[1] == 'after')):
        lines.insert(idx + 1 if pos == 'after' else idx, text)
    return len(edits) // 2


def main():
    src = open(TARGET, encoding='utf-8').read()
    if 'NTF_GUARD(' in src:
        print('Tweak.xm already carries the iOS 15 hardening; nothing to do')
        return 0

    report = []

    src, n = re.subn(r'^#import "Tweak\.h"$',
                     '#import "Tweak.h"\n#import <objc/runtime.h>',
                     src, count=1, flags=re.M)
    report.append(('import <objc/runtime.h>', n))

    if ANCHOR not in src:
        sys.stderr.write('error: helper anchor not found in Tweak.xm\n')
        return 1
    src = src.replace(ANCHOR, ANCHOR + HELPERS, 1)
    report.append(('helpers inserted', 1))

    src, n = re.subn(r'\[self _headerContentView\]',
                     'ntfHeaderContentViewForView(self)', src)
    report.append(('[self _headerContentView]', n))

    src, n = re.subn(
        r'MSHookIvar<MTPlatterHeaderContentView \*>\(\s*self,\s*"_headerContentView"\s*\)',
        'ntfHeaderContentViewForView(self)', src)
    report.append(('MSHookIvar _headerContentView', n))

    src, n = re.subn(r'\[self _notificationContentView\]',
                     'ntfNotificationContentViewForView(self)', src)
    report.append(('[self _notificationContentView]', n))

    src, n = re.subn(
        r'MSHookIvar<NCNotificationContentView \*>\(\s*self,\s*"_notificationContentView"\s*\)',
        'ntfNotificationContentViewForView(self)', src)
    report.append(('MSHookIvar _notificationContentView', n))

    src, n = re.subn(r'\[self _viewControllerForAncestor\]',
                     'ntfViewControllerForAncestor(self)', src)
    report.append(('[self _viewControllerForAncestor]', n))

    # Does not match the %new -backgroundMaterialView definition.
    src, n = re.subn(r'self\.backgroundMaterialView(?!\s*\{)',
                     'ntfBackgroundMaterialView(self)', src)
    report.append(('self.backgroundMaterialView', n))

    msh = re.compile(r'MSHookIvar<([^>]*)>\(\s*(.*?),\s*("(?:[^"]*)")\s*\)')
    src, n = msh.subn(
        lambda m: '((%s)ntfIvarNamed(%s, %s))'
                  % (m.group(1).strip(), m.group(2).strip(), m.group(3)), src)
    report.append(('MSHookIvar -> ntfIvarNamed', n))

    lines = src.split('\n')
    ins, rep = hoist_accessors(lines)
    src = '\n'.join(lines)
    report.append(('accessors hoisted (decl / sites)', '%d / %d' % (ins, rep)))

    lines = src.split('\n')
    guarded = guard_hook_bodies(lines)
    src = '\n'.join(lines)
    report.append(('hook bodies guarded', guarded))

    src = re.sub(r'NTF_GUARD\(@"-\[(\w+) \([^)]*\)', r'NTF_GUARD(@"-[\1 ', src)
    src = re.sub(r'^@try \{$', '    @try {', src, flags=re.M)
    src = re.sub(r'^\} NTF_GUARD\(', '    } NTF_GUARD(', src, flags=re.M)

    open(TARGET, 'w', encoding='utf-8').write(src)
    for name, n in report:
        print('  %-38s %s' % (name, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
