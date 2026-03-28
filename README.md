# [Tiny Glade](https://store.steampowered.com/app/2198150/Tiny_Glade/) JSON 3D Blender AddOn

## Installation
1. Download the zip file from the release page
2. Open Blender go to -> Edit -> Preferences -> Add-ons -> top right arrow down button -> Install from Disk -> select "tiny_glade_blender_add_on1.x.x.zip" -> click "Install from Disk" bottom right
## Usage 

* import *JSON* mesh files, there is a new **Import Type** selector in the file browser: choose **Tree** when loading tree files so that the vertex‑color data is split into a UV map (x/y) and a canopy flag (z).  
*Note:* the file format uses **1 = trunk, 0 = canopy**; the add‑on automatically flips this to the internal canopy flag.  

* The mesh edit vertex context menu (right‑click) also includes toggles for **Metal**, **Glass** and the new **Canopy** boolean attributes. Some mesh use those properties to assign the right material to each part.
* to see which vertex has those flag a new menu is available in the edit menu. toggle the "show attributes" checkbox ( sometimes you need to toggle it twice to make it work
  
* You can also export .JSON Files as the Tiny Glade Format. select the according pipeline normal or tree, and check the according checkbox to match the input file.

## here is an old video showing the add on: [YouTube](https://youtu.be/l3bbmhv0Qi0)

## questions?
I m always around the Tiny Glade Discord, fell free to ask @Rapunzilla if you have any questions or suggestions 

## Try the Tiny Glade [3D Model Viewer](https://github.com/FlazeIGuess/tinyglade-3dmodel-viewer/tree/master)
