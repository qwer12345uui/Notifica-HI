#import <UIKit/UIKit.h>

@class NEPPalette;

@interface NEPColorUtils : NSObject
+ (BOOL)isDark:(UIColor *)color;
+ (NEPPalette *)averageColors:(UIImage *)image withAlpha:(double)alpha;
+ (UIColor *)averageColorNew:(UIImage *)image withAlpha:(double)alpha;
+ (UIColor *)averageColor:(UIImage *)image withAlpha:(double)alpha;
+ (UIColor *)colorWithMinimumSaturation:(UIColor *)color withSaturation:(double)saturation;
@end
