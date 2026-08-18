#import <UIKit/UIKit.h>

@interface NEPColor : NSObject
@property (nonatomic, assign) unsigned long r;
@property (nonatomic, assign) unsigned long g;
@property (nonatomic, assign) unsigned long b;
@property (nonatomic, assign) unsigned long a;

+ (NEPColor *)fromLong:(unsigned long)color;
- (void)setLong:(unsigned long)color;
- (unsigned long)toLong;
+ (NEPColor *)fromUIColor:(UIColor *)color;
- (BOOL)isDark;
- (BOOL)isBlackOrWhite;
- (BOOL)isDistinct:(NEPColor *)color;
- (double)lum;
- (BOOL)isContrasting:(NEPColor *)color;
- (NEPColor *)saturate:(double)saturation;
- (UIColor *)uicolor;
- (UIColor *)uicolorWithAlpha:(double)alpha;
@end
