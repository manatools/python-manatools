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
    [ ] YBusyIndicator
    [ ] YLogView

Optional/special widgets (from `YOptionalWidgetFactory`):

    [X] YDumbTab
    [ ] YSlider
    [ ] YDateField
    [ ] YTimeField
    [ ] YBarGraph
    [ ] YPatternSelector (createPatternSelector)
    [ ] YSimplePatchSelector (createSimplePatchSelector)
    [ ] YMultiProgressMeter
    [ ] YPartitionSplitter
    [ ] YDownloadProgress
    [ ] YDummySpecialWidget
    [ ] YTimezoneSelector
    [ ] YGraph
    [ ] Context menu support / hasContextMenu

To check/review:
    how to manage YEvents [X] and YItems [X] (verify selection attirbute).

    [X] YInputField password mode
    [X] askForExistingDirectory
    [X] askForExistingFile
    [X] askForSaveFileName
    [ ] YAboutDialog (aka YMGAAboutDialog)
    [ ] adding factory create alternative methods (e.g. createMultiSelectionBox)
    [ ] managing shortcuts
    [ ] localization

Nice to have: improvements outside YUI API

    [ ] window title
    [ ] window icons
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
