### Items to address


#### The current constructed worksheet pdfs need some better formatting. 
  - While I've referred to them as boxes the visible effect should be a simple underline
  - font styling should roughly follow the same formatting for official IRS forms and schedules
  - No need to refer to 'worksheet entries'. Superfluous text not needed.
  - Header font should feel more like a federal form (same fonts etc)  Use header and subheader where appropriate
  - Page numbers should be more concise and informative ('page 1 of x')

#### Radio Boxes look ugly in the questionaires.  Fix.
  - I prefer mutually exclusive check boxes  (yes box and no box side by side.  
  - One can be checked or neither.  If the question is required (in most cases, it is required), then highlight in red background.
  - Remember that the .json should now have a default of null (or unanswered, etc) for yes/no questions.  This way the user is forced to answer.
  
#### Any form, worksheet, etc that is missing a required cell should be in red font on the left navigator panel.  We should maintain a state (complete or incomplete)

#### Info Returns with multiple copies:
  - we need a mechanism of adding and removing individual (like add a 1099-INT) and remove.  
  - This can be tricky.  If the one is removed manually , then the subsequent ones must be moved up.This may force reordering.

#### We need a more concise way to represent the forms in the left panel of the user app.  
  - This may require adding a field to the .json for each form that has a shorthand.
  - The display of the shortand in the left panel should indicate how many copies (for the items that can have multiple copies in one display, like 1099-INT, etc)
  - We probably want to display the multiple form types (like 1116, etc) that use different categories of income separately with the category shorthand in parens)
  