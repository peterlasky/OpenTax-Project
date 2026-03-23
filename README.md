# Open Tax Project

### The Challenge: 
Can we design a ```plan.md``` file sufficient for an LLM to recreate accurate and useable Federal tax software?

### Scope
In order to limit the scope of this exercise, I've created a .yaml of all the relevant items:
  - Forms and schedules
  - Instructions
  - Publications
  - Information Returns (W-2, 1099-INT, etc.)

Providing these isn't strictly necessary, but will limit scope.  For the current phase, the intended functional scope should not exceed `TurboTax Premier`. 

### Rules
  Create a plan.md that can guide an LLM from start to finish:
  - Manual entry of primary data
  - Creation of worksheets as described in instructions and publications
  - Flow through so no duplicate entries are needed
  - Correctly linking lines and cells with formulas
  - Filling in of forms for filing in .pdf format
  - Enforce formatting rules, heirarchy rules, etc.
  - Have the program autofill a pdf of the forms required for filing.
  
  Optional:
  - Allow information returns to be entered initially by scanning .pdfs issued by employers, financial institutions, etc.

### Motivation
  - Learn how to design a project that can prompt a model in a highly complex task.
  - What can be more complex than the US Tax Code?  (*answer: nothing*)

### Verdict so far
  **ChatGPT5.4 is not up to the task**  Not yet. Not without deep intervention from me.  
  - I couldn't get it to propose a comprehensive methodology on its own
  - I worked iteratively to refine the plan. 
  - After a few evenings of tinkering, prompting, and waiting, I was able to build a workable 1040 that filled in and could be print 

  
### Hints I gave it (which should have been unnecessary)
  - a list of all the relevant forms, instructions, publications, and information returns (all links to .pdfs). 
  - a thorough description of a `pyside.qt` spreadsheet-like GUI to enter, calculate, and view all the data



