The goal of this branch is to explore creating a pure-Python implementation of the libyui binding interface.

While libyui has been a valuable dependency for this project for many years (and continues to be in other branches), this move aims to remove the hard dependency. We hope this will provide a more manageable backend and facilitate a smoother transition for related tools, **especially for dnfdragora**.

As this is a non-profit project, we rely on developers who are contributing in their **very limited spare time**. To accelerate this effort, we are leveraging AI to assist with a significant portion of the development work.

Next is the starting todo list.

Missing Widgets comparing libyui:

    [ ] YComboBox (on going)
    [ ] YSelectionBox
    [ ] YMultiSelectionBox
    [ ] YTree
    [ ] YTable
    [ ] YProgressBar
    [ ] YRichText
    [ ] YMultiLineEdit
    [ ] YIntField
    [ ] YMenuButton, YMenuBar
    [ ] YWizard
    [ ] YPackageSelector
    [ ] YSpacing, YAlignment
    [ ] YReplacePoint
    [ ] YRadioButton, YRadioButtonGroup

To check how to manage YEvents and YItems.
