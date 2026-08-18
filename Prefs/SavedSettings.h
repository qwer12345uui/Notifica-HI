#import <Preferences/PSListController.h>
#import <Preferences/PSSpecifier.h>
#import <spawn.h>

@interface NTFSavedSettingsListController : PSViewController <UITableViewDelegate, UITableViewDataSource> {
    UITableView *_tableView;
}

@property (nonatomic, strong) UIBarButtonItem *importButton;
@property (nonatomic, strong) NSMutableArray *savedSettings;
@property (nonatomic, strong) NSString *selectedSettings;
- (void)refreshList;
@end
