"""

    This function takes the <name>.jpg and <name>.avi pairs like LabGym creates 
    and presents them to a user for sorting.  It overlays on this presentation a list of user
    definable keys to behavior mapping that can be used to move the image/animation pairs
    to the correct output directory. IDEALLY, a "junk" option will be included in this list
    so that if a session is terminated and restarted and images not desired will not need 
    to be reprocessed!  
    
    The available user inputs while sorting will be:
    -keys mapped to desired behaviors. (including a junk option)
    -<right_arrow> and <left_arrow> can be used to go to next/previous pair without taking any action
    -<u> is mapped to the multilevel undo function which undoes a category assignment and returns the pairs for sorting

    inputs:
    1) input image directory: this is the top level directory that LabGym stored image/video pairs within.  There
    will usually be subfolders with animal numbers a dn then the pairs within those folder.  point toward the highest
    level folder containing all folders you want to process.  It will walk them all.
    2) output directory: the program will create a "categories" folder here and then the subfolders for each
    behavior where you will sort the images.  you do not need to create these folders in advance.  This the folders
    exist already, they will be used and the output will be merged into the directory.
    3) category name/key pairs: The input format must be category1{key1}, category2{key2}, etc. It is a good idea to
    create a "junk" category with a key mapping to dispose of bad samples.  Just remember to delete that folder before
    doing additional processing or else you could accidentally train a "junk" behavior.  Please note that the
    key "u" is reserved for the undo function.

"""

import os
import cv2
import shutil
import numpy as np
import wx
import time
import re
from natsort import natsorted


class SortingHat():

    # Setup the variables we need for SortingHat
    def __init__(self):
        self.behavior_names = []
        self.behavior_key_mapping = []
        self.input_image_directory = None
        self.output_image_directory = None
        self.remove_empty_frames = True
        self.image_display_sizes = 0, 0
        self.undo_key = None
        self.right_arrow = 316
        self.left_arrow = 314
        self.behavior_sample_paths = None
        self.category_directories = None
        self.category_strings = None
        self.undo_list = [[], [], []]
        self.label_scale = 20
        self.label_height = np.inf
        self.label_width = np.inf
        self.current_index = 0
        self.image_name = None
        self.video_name = None
        self.cap = None
        self.display_image = None
        self.video_location = None
        self.video = None
        self.video_location = None
        self.video = None
        self.video_frames = []
        self.timer_interval = None

    # Fill in the SortingHat variables and including building the map of behaviors to keys
    # some of this will likely be simplified in the future using tuples
    # For the wxpython (gui) version, <esc> was removed as an exit because the user can just close the window
    def prepare_hat(self, behavior_names=[], behavior_key_mapping=[],
                    input_image_directory='', output_image_directory=os.getcwd(),
                    remove_empty_frames=True, image_display_sizes=(600, 600), undo_key='U'):
        self.behavior_names = behavior_names
        self.behavior_key_mapping = behavior_key_mapping
        self.input_image_directory = input_image_directory
        self.output_image_directory = output_image_directory
        self.remove_empty_frames = remove_empty_frames
        self.image_display_sizes = image_display_sizes
        self.undo_key = undo_key
        self.behavior_sample_paths = []

        for root, dirs, files in os.walk(self.input_image_directory, topdown=False):
            for name in files:
                if name.endswith('.avi'):
                    self.behavior_sample_paths.append((root, name[:-4]))
        if not self.behavior_sample_paths:
            wx.MessageBox("No Samples in the Input folder", "Complete!", wx.OK | wx.ICON_INFORMATION)
            self.Close()
        self.behavior_sample_paths = natsorted(self.behavior_sample_paths)
        self.category_directories = []
        self.category_strings = []
        for i in range(len(self.behavior_names)):
            self.category_strings.append((self.behavior_key_mapping[i]) + ': ' + self.behavior_names[i])
            if not os.path.exists(os.path.join(self.output_image_directory, 'categories', self.behavior_names[i])):
                os.makedirs(os.path.join(self.output_image_directory, 'categories', self.behavior_names[i]))
            self.category_directories.append(
                os.path.join(self.output_image_directory, 'categories', self.behavior_names[i]))
        self.category_strings.append("U: Undo")
        self.scale_text()
        self.update_image_pointer()

    def scale_text(self):
        # walk through the category label and pick a scaling factor such that they all fit vertically and
        # only take up 10% of the horizontal space (centered) and 70% of the vertical space
        self.label_scale = 100
        self.label_height = np.inf
        self.label_width = np.inf
        for j in range(len(self.category_strings)):
            while self.label_height > (self.image_display_sizes[1] / len(self.category_strings)) * .7:
                self.label_scale = self.label_scale * .9
                (self.label_width, self.label_height), baseline = cv2.getTextSize(self.category_strings[j],
                                                                                  cv2.FONT_HERSHEY_SIMPLEX,
                                                                                  self.label_scale,
                                                                                  int(2 * self.label_scale))
                self.label_height = self.label_height + baseline
            while self.label_width > (self.image_display_sizes[0] * 2 * .1):
                self.label_scale = self.label_scale * .9
                (self.label_width, self.label_height), baseline = cv2.getTextSize(self.category_strings[j],
                                                                                  cv2.FONT_HERSHEY_SIMPLEX,
                                                                                  self.label_scale,
                                                                                  int(2 * self.label_scale))
                self.label_height = self.label_height + baseline

    def update_image_pointer(self):
        while True:
            # Load the latest file name into the image_name and video_name with correct extension
            self.image_name = os.path.join(self.behavior_sample_paths[self.current_index][0],
                                           self.behavior_sample_paths[self.current_index][1] + ".jpg")
            self.video_name = os.path.join(self.behavior_sample_paths[self.current_index][0],
                                           self.behavior_sample_paths[self.current_index][1] + ".avi")

            # open and display the image that will be used to categorize the animal
            # catch the error that the file doesn't exist or has moved since sorting started so the
            # program doesn't crash.  Instead, remove it from the list and continue
            try:
                self.display_image = cv2.imread(self.image_name)
                self.display_image = cv2.resize(self.display_image, dsize=self.image_display_sizes,
                                                interpolation=cv2.INTER_CUBIC)
            except:
                print(f"The image file was not present: {self.image_name}")
                self.behavior_sample_paths.remove(self.behavior_sample_paths[self.current_index])
                return

            # open the video that will be used to categorize the animal
            # catch the error that the file doesn't exist or has moved since sorting started so the
            # program doesn't crash.  Instead, remove it from the list and continue
            try:
                self.cap = cv2.VideoCapture(self.video_name)
            except:
                print(f"The video file was not present: {self.image_name}")
                self.behavior_sample_paths.remove(self.behavior_sample_paths[self.current_index])
                return

            # If we want to ignore/remove pairs whose avi files have empty frames in them
            # then loop through the avi frames and make sure they ALL have some content
            # if ANY of the frames are empty then skip this file.  Note: it will not delete or remove the files
            # from the directory so this can cause the appearance of residual files after a sorting session. May
            # change this behavior in the future
            if self.remove_empty_frames:
                found_empty = False
                while True:
                    _, frame = self.cap.read()
                    if frame is None:
                        break
                    if not frame.any():
                        found_empty = True
                        break

                # If we found an empty frame, remove the filename from out list and print out the filename to
                # the console if commented
                if found_empty:
                    self.behavior_sample_paths.remove(self.behavior_sample_paths[self.current_index])
                    print("Found empty frame in: " + self.behavior_sample_paths[self.current_index][0] + "/" +
                          self.behavior_sample_paths[self.current_index][1])
                    if not self.behavior_sample_paths:
                        return
                else:
                    self.cap.set(cv2.CAP_PROP_POS_MSEC, 0)
                    return

    # Dynamically playing (looping) through the video frame also calls a "rescale" function internally within wxpython
    # however "rescale" is not optimized at all and therefore spikes the CPU and causes the video to play slowly.
    # This function buffers the video frames after scaling them therefore the can be played on screen rapidly
    # without performance issue. It is called every time a new video/image pair are selected or when the
    # window is resized.
    def load_new_video(self):
        self.video_frames = []
        try:
            self.video = self.cap
            self.display_image = self.display_image
        except:
            print(f"The video file was not present: {self.image_name}")
            self.behavior_sample_paths.remove(self.behavior_sample_paths[self.current_index])
            return

        while True:
            _, frame = self.video.read()
            if frame is None:
                break
            else:
                self.video_frames.append(cv2.resize(frame, self.image_display_sizes))
                frame = cv2.resize(frame, dsize=self.image_display_sizes, interpolation=cv2.INTER_CUBIC)
                horizontal_concat = np.concatenate((self.display_image, frame), axis=1)

                # draw the category labels onto the display image
                for j in range(len(self.category_strings)):
                    cv2.putText(horizontal_concat, self.category_strings[j],
                                (int(self.image_display_sizes[0] - self.label_width / 2),
                                 self.label_height * (j + 1) + 1),
                                cv2.FONT_HERSHEY_SIMPLEX, self.label_scale, (255, 0, 0), int(self.label_scale * 2))
                self.video_frames[-1] = horizontal_concat
                height, width = self.video_frames[-1].shape[:2]
                image = wx.Image(width, height)
                image.SetData(self.video_frames[-1])
                self.video_frames[-1] = image.ConvertToBitmap()
        self.timer_interval = self.video.get(cv2.CAP_PROP_FPS)


# This is the class to draw the actual sortingHat and receive user input
class SortingHatFrame(wx.Frame):

    def __init__(self, parent, input_directory=os.getcwd(), output_directory=os.path.join(os.getcwd(), 'output/'),
                 categories=["junk"], category_mapping=["0"]):

        # Start by creating a basic, resizeable from that accepts character input and is resizable.
        # The default size was arbitrarily chosen at 1200 wide by 600 high
        wx.Frame.__init__(self, parent, style=wx.WANTS_CHARS | wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER,
                          title="SortingHat", size=(1200, 600))

        # Declare a new SortingHat
        self.sort = SortingHat()

        # these are sample categories which could be used
        # categories = ['junk', 'curling', 'crawling', 'immobile', 'rolling', 'turning', 'uncoiling']
        # category_mapping = ['0', '1', '2', '3', '4', '5', '6']

        # Initialize the data into the SortingHat which we captured in the initial gui
        # thing that must be captured in advance are categories, category_mapping, input and output directories
        # this could be enhanced to also take the dfault window size, but it doesn't seem necessary at this time
        self.sort.prepare_hat(categories,
                              category_mapping,
                              input_directory,
                              output_directory,
                              True,
                              (600, 600))

        # Make the Panel that we will draw the Sorting Hat Images onto
        self.panel = wx.Panel(self, wx.ID_ANY, size=(1200, 600))

        # Center the SortingHatFrame on the screen
        self.Centre()

        # Bind a timer event to the panel.  This is used to play through (draw) the video frames to the panel
        self.panel.Bind(wx.EVT_TIMER, self.evt_timer)
        self.panel.timer = wx.Timer(self.panel)

        # Establish the current image and video to be displayed
        self.sort.update_image_pointer()
        self.sort.load_new_video()
        self.video_frame = 0

        # Bind to the Panel the capture of key input to when a key is pressed down
        self.panel.Bind(wx.EVT_KEY_DOWN, self.evt_on_key_event)

        # Bind the Paint event to the SortingHatFrame
        self.Bind(wx.EVT_PAINT, self.evt_on_paint)

        # Bind the resize event to the SortingHatFrame
        self.Bind(wx.EVT_SIZE, self.evt_on_resize)

        # Start the timer.
        self.panel.timer.Start(milliseconds=(int(1000 / self.sort.timer_interval)))

    # Function: restart_timer
    # Description: simple function to restart the timer with a new interval based on the current video
    # This ensures that all sample play at their own appropriate frame rate
    def restart_timer(self):
        self.panel.timer.Stop()
        self.panel.timer.Start(milliseconds=(int(1000 / self.sort.timer_interval)))

    # Function: evt_on_key_event
    # Description: captures key input from the user and then take the appropriate action
    # 1) Move forward and backward through the files based on the arrows
    # 2) Move the files to the correct category folder if mapped
    # 3) Undo the previous move if the user presses "u"
    # 4) ignore the key input if it didn't match anything in items 1 -> 3 above
    def evt_on_key_event(self, event):
        # keep this print statement here for future key capture debugging if required
        # print("Modifiers: {} Key Code: {}".format(event.GetModifiers(), event.GetKeyCode()))

        # Get the Key that the user pressed
        k = event.GetKeyCode()
        # if the left arrow is pressed and you are not at the first image already, go back one image
        if (k == self.sort.left_arrow) and (self.sort.current_index > 0):
            self.sort.current_index -= 1
            self.sort.update_image_pointer()
            self.sort.load_new_video()
            self.restart_timer()
            return

        # if the right arrow is pressed and you are not at the end of the images, go to the next image
        elif (k == self.sort.right_arrow) and (self.sort.current_index >= 0) and \
                (self.sort.current_index < (len(self.sort.behavior_sample_paths) - 1)):
            self.sort.current_index += 1
            self.sort.update_image_pointer()
            self.sort.load_new_video()
            self.restart_timer()
            return

        # if the pressed key is one that has been assigned to a category, then move the file to the correct folder
        elif str(chr(k)) in self.sort.behavior_key_mapping:
            file_name = self.sort.behavior_sample_paths[self.sort.current_index][1]

            # move the file to the correct category directory corresponding to its index in the directory list
            shutil.move(self.sort.image_name,
                        os.path.join(self.sort.category_directories[self.sort.behavior_key_mapping.index(str(chr(k)))],
                                     file_name + ".jpg"))
            shutil.move(self.sort.video_name,
                        os.path.join(self.sort.category_directories[self.sort.behavior_key_mapping.index(str(chr(k)))],
                                     file_name + ".avi"))

            # write the full filename, and it's index when removed, into the undo list
            self.sort.undo_list[0].append(
                [self.sort.category_directories[self.sort.behavior_key_mapping.index(str(chr(k)))], file_name])
            self.sort.undo_list[1].append(self.sort.current_index)
            self.sort.undo_list[2].append(self.sort.behavior_sample_paths[self.sort.current_index])

            # remove the image name from the tuple list of images to sort
            self.sort.behavior_sample_paths.remove(self.sort.behavior_sample_paths[self.sort.current_index])

            # if this isn't the first image, go to the previous image next
            if not self.sort.behavior_sample_paths:
                wx.MessageBox("Done Processing Images", "Complete!", wx.OK | wx.ICON_INFORMATION)
                self.Close()
            elif self.sort.current_index >= (len(self.sort.behavior_sample_paths) - 1):
                self.sort.current_index -= 1
                self.sort.update_image_pointer()
                self.sort.load_new_video()
                self.restart_timer()
            else:
                self.sort.update_image_pointer()
                self.sort.load_new_video()
                self.restart_timer()
            return

        # if the user hit the undo ('u') key, then undo the last action
        elif (str(chr(k)) == self.sort.undo_key) and (len(self.sort.undo_list[0]) > 0):

            # get the path the files went to (sorted_path) and the original path
            # then create image and video names to make the code simpler to read
            sorted_path = self.sort.undo_list[0][-1][0]
            original_path = self.sort.undo_list[2][-1][0]
            image_name = self.sort.undo_list[0][-1][1] + ".jpg"
            video_name = self.sort.undo_list[0][-1][1] + ".avi"

            # move the video and image back to the original directory and out of the category folder
            shutil.move(os.path.join(sorted_path, image_name), os.path.join(original_path, image_name))
            shutil.move(os.path.join(sorted_path, video_name), os.path.join(original_path, video_name))

            # insert the file name back in the correct place in the image name list
            self.sort.behavior_sample_paths.insert(self.sort.undo_list[1][-1], self.sort.undo_list[2][-1])

            # remove the file name and its index from the undo list
            self.sort.undo_list[0].pop()
            self.sort.undo_list[1].pop()
            self.sort.undo_list[2].pop()

            # set the current image to be sort to the one we just moved back through undo
            self.sort.update_image_pointer()
            self.sort.load_new_video()
            self.restart_timer()
            return

        # if any other key is pressed, go back and keep waiting for a valid key entry
        # this gives us a place to debug (print) unmatched key presses in the future if needed
        else:
            # uncomment the next line to debug key presses
            # if not k == 255: print(str(k))
            return

    # Function: evt_timer
    # Description: runs whenever the timer event triggers painting the latest video image
    def evt_timer(self, event):
        # check to be sure that the image size and current size of the frame match, if not fix it
        if self.Size != (self.sort.image_display_sizes[0] * 2, self.sort.image_display_sizes[0]):
            self.sort.update_image_pointer()
            self.sort.load_new_video()
            self.restart_timer()

        # Run the function to paint the image to the panel
        self.evt_on_paint(None)

        # If it is the first video frame, pause for 0,5 so that users notice where the begging of the video is at
        if self.video_frame == 0: time.sleep(0.5)

        # Increment the frame index to the next frame
        self.video_frame += 1

    # Function: evt_on_paint
    # Description: It paints a new video frame whenever repainting is required and called by the timer event
    def evt_on_paint(self, event):

        # this must be declared to paint on the window
        dc = wx.PaintDC(self)

        # If it is not the last stored frame, paint it.  otherwise go back to the first frame and then paint.
        if self.video_frame < len(self.sort.video_frames):
            frame = self.sort.video_frames[self.video_frame]
            dc.DrawBitmap(frame, 0, 0, False)
        else:
            self.video_frame = 0
            frame = self.sort.video_frames[self.video_frame]
            dc.DrawBitmap(frame, 0, 0, False)

    # Function: evt_on_resize
    # Description: Called whenever the window is resized.  It creates/loads video frames at the appropriate new size
    def evt_on_resize(self, event):
        temp = self.Size
        self.panel.size = temp
        self.sort.scale_text()
        self.sort.update_image_pointer()
        self.sort.load_new_video()
        self.restart_timer()
        self.sort.image_display_sizes = (int(temp[0] / 2 + 0.5), temp[1] - 20)
        # self.panel.Size=(temp[1],temp[1])
        # print(self.sort.image_display_sizes)

    def onClose(self, event):
        self.Close()


# Class: SortingHat_InitialWindow
# Description: This class was taken from LabGym and then modified for User input for sortinghat
# Its goal is to get the input and output paths as well as the category name <-> key mappings
class SortingHatInitialWindow(wx.Frame):

    def __init__(self, title):
        # if want to adjust the size, add arg 'size=(x,y)' but this size seems fine
        super(SortingHatInitialWindow, self).__init__(parent=None, title=title, size=(450, 275))

        # Set up the variables that we want to capture
        self.input_directory = None
        self.output_directory = None
        self.categories = []
        self.category_mapping = []
        self.display_window()
        self.undo_key = 'U'

    def display_window(self):
        panel = wx.Panel(self)
        boxsizer = wx.BoxSizer(wx.VERTICAL)

        # add some vertical spacing
        boxsizer.Add(0, 30, 0)

        # add the button to get the input directory and bind its event function
        button1 = wx.Button(panel, label='Select Input Directory')
        boxsizer.Add(button1, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 40)
        button1.Bind(wx.EVT_BUTTON, self.evt_get_input_directory)

        # add some vertical spacing
        boxsizer.Add(0, 30, 0)

        # add the button to get the output directory and bind its event function
        button2 = wx.Button(panel, label='Select Output Directory')
        boxsizer.Add(button2, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 40)
        button2.Bind(wx.EVT_BUTTON, self.evt_get_output_directory)

        # add some vertical spacing
        boxsizer.Add(0, 30, 0)

        # add the button to get the category list and bind its event function
        button3 = wx.Button(panel, label='Enter Categories')
        boxsizer.Add(button3, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 40)
        button3.Bind(wx.EVT_BUTTON, self.evt_enter_categories)

        # add some vertical spacing
        boxsizer.Add(0, 30, 0)

        # add the button to start the SortingHat and bind its event function
        button5 = wx.Button(panel, label='Analyze Behaviors')
        boxsizer.Add(button5, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 40)
        button5.Bind(wx.EVT_BUTTON, self.evt_start_sorting)

        # finish the panel setup and show the window centered on screen
        panel.SetSizer(boxsizer)
        self.Centre()
        self.Show(True)

    # Function: evt_get_input_directory
    # Description: basic modal directory dialog box to get the input directory
    def evt_get_input_directory(self, event):
        dlg = wx.DirDialog(None, "Choose input directory", "",
                           wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.input_directory = dlg.GetPath()
        dlg.Destroy()

    # Function: evt_get_output_directory
    # Description: basic modal directory dialog box to get the output directory
    def evt_get_output_directory(self, event):
        dlg = wx.DirDialog(None, "Choose output directory", "",
                           wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.output_directory = dlg.GetPath()
        dlg.Destroy()

    # Function: evt_enter_categories
    # Description: text entry modal dialog to get the category names and key mappings
    # the input format must be category1{key1}, category2{key2}, etc
    # It is a good idea to create a junk category with a key mapping to dispose of bad samples
    def evt_enter_categories(self, event):

        # Set the default text value to the current category/key mappings so they can be edited if desired
        existing_category_mappings = ""
        if self.category_mapping:
            for i in range(len(self.category_mapping)):
                existing_category_mappings += str(self.categories[i]) + "{" + str(self.category_mapping[i]) + "}"
                if i < (len(self.category_mapping) - 1):
                    existing_category_mappings += ","

        dlg = wx.TextEntryDialog(self, 'Enter your categories separated by commas.  '
                                       '\n\nFormat: category1{key}, category2{key2}, etc'
                                       '\n', 'Category Entry', value=existing_category_mappings)

        # Only process the input if the user pressed OK.  if the pressed cancel, the don't do anything
        while True:
            if dlg.ShowModal() == wx.ID_OK:
                txt = dlg.GetValue()
                temp_categories = []
                temp_category_mapping = []

                # Ensure the user entered something
                if len(txt):

                    # split the string into comma separated values of category{key} for each
                    x = txt.split(",")

                    # loop through the category/key pairs
                    for i in range(len(x)):

                        # strip off any whitespaces
                        temp = str(x[i].strip())

                        # split the cae4gory name and key mappings
                        temp2 = re.split('{|}', temp)

                        # make sure that a name and key mapping were provided
                        if len(temp2) > 1:

                            # Ensure the category key is only 1 character long
                            if len(temp2[1].strip()) == 1:

                                # Check that there are no keys values match the *reserved* undo key "u"
                                if str(temp2[1].strip()) == self.undo_key.upper() or \
                                        str(temp2[1].strip()) == self.undo_key.lower():
                                    temp_category_mapping = []
                                    temp_categories = []
                                    wx.MessageBox(temp2[1].strip() + " is reserved as the Undo Key Value\n"
                                                                     "Check your entry data", "Error",
                                                  wx.OK | wx.ICON_INFORMATION)

                                # Check that there are not duplicated category names or key values
                                elif (temp2[1].strip() in temp_category_mapping) or \
                                        (str(temp2[0].strip()) in temp_categories):
                                    temp_category_mapping = []
                                    temp_categories = []
                                    wx.MessageBox("Category and Key Mapping Duplicate Found. \n "
                                                  "Check your entry data", "Error",
                                                  wx.OK | wx.ICON_INFORMATION)
                                else:
                                    temp_category_mapping.extend(temp2[1].strip())
                                    temp_categories.append(str(temp2[0].strip()))
                            else:
                                temp_category_mapping = []
                                temp_categories = []
                                wx.MessageBox("Category Key Mapping Incorrect \n "
                                              "Value must be only a single character \n"
                                              "Format: name{character}",
                                              "Error", wx.OK | wx.ICON_INFORMATION)
                                break
                        else:
                            temp_category_mapping = []
                            temp_categories = []
                            wx.MessageBox("Category and Key Mapping Incorrect", "Error", wx.OK | wx.ICON_INFORMATION)
                            break

                    # If the entry was successful then set the values and exit the dialog and continue
                    if temp_category_mapping:
                        self.category_mapping = temp_category_mapping
                        self.categories = temp_categories
                        return

                # If the user pressed the cancel button, then give up leaving the mapping as they were
            else:
                break

    def evt_start_sorting(self, event):
        if self.input_directory is None:
            wx.MessageBox("No Input Directory Provided", "Error", wx.OK | wx.ICON_INFORMATION)
        elif self.output_directory is None:
            wx.MessageBox("No Output Directory Provided", "Error", wx.OK | wx.ICON_INFORMATION)
        elif len(self.categories) == 0:
            wx.MessageBox("No Categories Provided", "Error", wx.OK | wx.ICON_INFORMATION)
        else:
            Hat = SortingHatFrame(None, self.input_directory, self.output_directory, self.categories, self.category_mapping)
            Hat.Show()


# Run the program
if __name__ == '__main__':
    app = wx.App()
    SortingHatInitialWindow('LabGym Sorting Hat')
    app.MainLoop()