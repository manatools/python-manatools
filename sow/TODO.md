The goal of this branch is to explore creating a pure-Python implementation of the libyui binding interface.

While libyui has been a valuable dependency for this project for many years (and continues to be in other branches), this move aims to remove the hard dependency. We hope this will provide a more manageable backend and facilitate a smoother transition for related tools, **especially for dnfdragora**.

As this is a non-profit project, we rely on developers who are contributing in their **very limited spare time**. To accelerate this effort, we are leveraging AI to assist with a significant portion of the development work.

Next is the starting todo list.

Missing Widgets comparing libyui original factory:

    [X] YComboBox
    [X] YSelectionBox
    [X] YMultiSelectionBox (implemented as YSelectionBox + multiselection enabled)
    [X] YPushButton
    [X] YLabel
    [X] YInputField
    [X] YCheckBox
    [X] YTree
    [X] YFrame
    [X] YTable (merging YMGACBTable)
    [X] YProgressBar
    [X] YRichText
    [X] YMultiLineEdit
    [X] YIntField
    [X] YMenuBar
    [X] YSpacing (detailed variants: createHStretch/createVStretch/createHSpacing/createVSpacing/createSpacing)
    [X] YAlignment helpers (createLeft/createRight/createTop/createBottom/createHCenter/createVCenter/createHVCenter)
    [X] YReplacePoint
    [X] YRadioButton
    [X] YImage
    [X] YBusyIndicator
    [X] YLogView

Optional/special widgets (from `YOptionalWidgetFactory`):

    [X] YDumbTab
    [X] YSlider
    [X] YDateField
    [X] YTimeField

To check/review:
    how to manage YEvents [X] and YItems [X] (verify selection attirbute).

    [X] YInputField password mode
    [X] askForExistingDirectory
    [X] askForExistingFile
    [X] askForSaveFileName
    [X] YAboutDialog (aka YMGAAboutDialog) - Implemented in manatools.ui
    [X] adding factory create alternative methods (e.g. createMultiSelectionBox)
    [X] managing shortcuts (only menu and pushbutton)
    [ ] localization

Nice to have: improvements outside YUI API

    [X] window title
    [X] window icons
    [ ] Context menu support
    [ ] selected YItem(s) in event
    [ ] Improving YEvents management (adding info on widget event containing data
        such as item selection/s, checked item, rich text url, etc.)

Skipped widgets:
    
    [-] YPackageSelector  (not ported)
    [-] YRadioButtonGroup (not ported)
    [-] YWizard           (not ported)
    [-] YItemSelector     (not ported)
    [-] YEmpty            (not ported)
    [-] YSquash / createSquash (not ported)
    [-] YMenuButton (legacy menus)
    [-] YBarGraph
    [-] YPatternSelector (createPatternSelector)
    [-] YSimplePatchSelector (createSimplePatchSelector)
    [-] YMultiProgressMeter
    [-] YPartitionSplitter
    [-] YDownloadProgress
    [-] YDummySpecialWidget
    [-] YTimezoneSelector
    [-] YGraph
    [-] Context menu support / hasContextMenu

Documentation gaps and recommendations
--------------------------------------
During review of backend implementations, several simple accessors and setters lack explicit docstrings. To improve developer experience:

1. Add concise docstrings to all public getters/setters in:
   - yui_qt.py (e.g., iconBasePath, setIconBasePath, productName)
   - yui_gtk.py (same setters/getters, note GTK version dependencies)
   - yui_curses.py (document NCurses-specific behaviors and filter parsing)
2. Document file chooser semantics and supported filter syntax for NCurses and GTK fallbacks.
3. Add a short README or reference page (this file) in the repository to explain expected cross-backend behavior and caveats.

Checklist for maintainers
-------------------------
- [ ] Add one-line docstrings to all public methods in YApplication* classes.
- [ ] Document minimum runtime dependencies and GTK/Qt version notes.
- [ ] Provide examples for common tasks (file chooser, setting icon/title) in README or docs.
- [ ] Ensure unit tests or integration tests cover file chooser fallbacks.
