import bpy
import sys
import os

def main():
    argv = sys.argv
    if "--" in argv:
        filepath = argv[argv.index("--") + 1]
        # Resolve to absolute
        abs_path = os.path.abspath(filepath)
        bpy.ops.wm.save_as_mainfile(filepath=abs_path)
        print(f"[Vertex] Created empty file: {abs_path}")

if __name__ == "__main__":
    main()
