# LabGymSortingHat ReadMe

In LabGym, the process is:
1. Use LabGym to generate *potential* behavior examples from a video of your animal.
2. Sort the examples into directories based on which behavior you, the observer, believe the examples to represent. 
3. Run the second half of LabGym on the directories the user manually created to ‘train’ AI model to automatically detect the behavior in future videos. 

The manual process of properly identifying and sorting the sample in step two was extremely monotonous and prone to errors while copying files from one directory to another by hand. 

To speed up this process and decrease errors associated with manually moving the files, I created LabGymSortingHat as a standalone program. This may be integrated into LabGym in the future, but for now it can be run independently. 

To use it, start the LabGymSortingHat GUI, point it at the directory in which LabGym stored its output from step 1. Then, select an output directory to store the categorized examples. Finally, add a behavior-to-hotkey mapping and initiate the sorting process.  

That’s it. LabGymSortingHat will create directories based on the behavior categories you want, and then when you press the hotkeys it will automagically move the files into the correct directory.  

A few final notes:
1. “u” is mapped to mean “undo”.  We all make mistakes so this will move the last file set back and allow you to re-sort it. This is an unlimited depth undo so you can undo all the way back to the beginning of that sorting session.
2. The right and left arrow keys allow you to move within the images without sorting in case you want to see what the other samples look like before sorting. You may sort any example along the way. There is no need to go back to the beginning to start sorting.
3. You can terminate the sorting session at any point by simply closing the window. You can resume the session at any point by simply ensuring you select the same input and output directories.
4. By default, any video sample to be sorted must have zero empty, blank, frames. Blank frames will cause poor behavior identification during training if they make it into the training dataset. Therefore, any video determined to have one or more blank frames will be skipped and never presented to the user. A message noting the skipped file is output to the terminal.

Happy sorting!
 
