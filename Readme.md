# DSTAnimTool

## Feature

Compile and decompile anim.bin and build.bin from anim.zip of DST.
Will also generate an `atlas.xml` for each `atlas.tex`, which can be use in [textools](https://github.com/zxcvbnm3057/dont-starve-tools) to view and export any png used in this animation while decompile `build.bin`. However, you can never get origin picture filename because the name did not exist in animation after compilation

## How to use

```bash
python [script_name] [path_to_working_folder]
```

- Require python2.7 which is part of Don't Starve Mod Tools.
- The script_name should be the script file you need.
- The folder by pass to script is the decompressed folder of your anim.zip. whitch contains `build.bin`, `anim.bin`, `atlas-0.tex` normally.

## For developers

If you wonder why this work, You may refer to the following files
- `Don't Starve Mod Tools\mod_tools\tools\scripts\buildanimation.py`  
- `Don't Starve Mod Tools\mod_tools\buildtools\windows\Python27\Lib\site-packages\klei\atlas.py`
