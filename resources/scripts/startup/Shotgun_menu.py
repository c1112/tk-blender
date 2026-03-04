# ----------------------------------------------------------------------------
# Copyright (c) 2020, Diego Garcia Huerta.
#
# Your use of this software as distributed in this GitHub repository, is
# governed by the Apache License 2.0
#
# Your use of the Shotgun Pipeline Toolkit is governed by the applicable
# license agreement between you and Autodesk / Shotgun.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


import ctypes
import os
import sys
import importlib.util
import time
import ast
import inspect

import bpy
from bpy.types import Header, Menu, Panel, Operator
from bpy.app.handlers import load_factory_startup_post, persistent, load_post

import site

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

ext_libs = os.environ.get("PYSIDE2_PYTHONPATH")

if ext_libs and os.path.exists(ext_libs):
    if ext_libs not in sys.path:
        print("Added path: %s" % ext_libs)
        site.addsitedir(ext_libs)

bl_info = {
    "name": "Shotgun Bridge Plugin",
    "description": "Shotgun Toolkit Engine for Blender",
    "author": "Diego Garcia Huerta",
    "license": "GPL",
    "deps": "",
    "version": (1, 0, 0),
    "blender": (2, 82, 0),
    "location": "Shotgun",
    "warning": "",
    "wiki_url": "https://github.com/diegogarciahuerta/tk-blender/releases",
    "tracker_url": "https://github.com/diegogarciahuerta/tk-blender/issues",
    "link": "https://github.com/diegogarciahuerta/tk-blender",
    "support": "COMMUNITY",
    "category": "User Interface",
}


PYSIDE_MISSING_MESSAGE = (
    "\n"
    + "-" * 80
    + "\nCould not import PySide2 or PySide6 as a Python module. Shotgun menu will not be available."
    + "\n\nPlease check the engine documentation for more information:"
    + "\nhttps://github.com/diegogarciahuerta/tk-blender/edit/master/README.md\n"
    + "-" * 80
)

try:
    from PySide6 import QtWidgets, QtCore

    PYSIDE_IMPORTED = True
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore

        PYSIDE_IMPORTED = True
    except ImportError:
        PYSIDE_IMPORTED = False


class ShotgunConsoleLog(bpy.types.Operator):
    """
    A simple operator to log issues to the console.
    """

    bl_idname = "shotgun.logger"
    bl_label = "Shotgun Logger"

    message: bpy.props.StringProperty(name="message", description="message", default="")

    level: bpy.props.StringProperty(name="level", description="level", default="INFO")

    def execute(self, context):
        self.report({self.level}, self.message)
        return {"FINISHED"}


_qt_app = None


def _process_qt_events():
    """Process Qt events via Blender's timer system."""
    if _qt_app is not None:
        # Skip during Windows drag/resize modal loops to prevent deadlock.
        # GetCapture() is non-NULL whenever a window holds mouse capture (e.g. resize, move).
        if sys.platform == "win32" and ctypes.windll.user32.GetCapture():
            return 0.001
        _qt_app.processEvents()
    return 0.001


class TOPBAR_MT_shotgun(Menu):
    """
    Creates the Shotgun top level menu
    """

    bl_label = "Shotgun"
    bl_idname = "TOPBAR_MT_shotgun"

    def draw(self, context):
        import sgtk

        engine = sgtk.platform.current_engine()
        if engine:
            engine.display_menu()


def insert_main_menu(menu_class, before_menu_class):
    """
    This function allows adding a new menu into the top menu bar in Blender,
    inserting it before another menu specified.

    In order to be changes proof, this function collects the code for the
    Operator that creates the top level menus, and modifies it by using
    python AST (Abstract Syntax Trees), finds where the help menu is appended,
    and inserts a new AST node in between that represents our new menu.

    Then it is a matter of registering the class for Blender to recreate it's
    own top level menus with the additional

    A bit overkill, but the alternative was to copy&paste some Blender original
    code that could have changed from version to version. (if fact it did
    change from minor version to minor version while developing this engine.)

    """

    # This is an AST nodetree that represents the following code:
    # layout.menu("<menu_class.__name__>")
    # which will ultimately be inserted before the menu specified.
    sg_ast_expr = ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="layout", ctx=ast.Load()), attr="menu", ctx=ast.Load()
            ),
            args=[ast.Constant(value=menu_class.__name__)],
            keywords=[],
        )
    )

    # get the source code for the top menu bar menus
    code = inspect.getsource(bpy.types.TOPBAR_MT_editor_menus)
    code_ast = ast.parse(code)

    # find the `draw` method
    function_node = None
    for node in ast.walk(code_ast):
        if isinstance(node, ast.FunctionDef) and node.name == "draw":
            function_node = node
            break

    # find where the help menu is added, and insert ours right before it
    for i, node in enumerate(function_node.body):
        if isinstance(node, ast.Expr) and before_menu_class.__name__ in ast.dump(node):
            function_node.body.insert(i - 1, sg_ast_expr)
            break

    # make sure line numbers are fixed
    ast.fix_missing_locations(code_ast)

    # compile and execute the code
    code_ast_compiled = compile(code_ast, filename=__file__, mode="exec")
    exec(code_ast_compiled)

    # the newly create class is now within the local variables
    return locals()["TOPBAR_MT_editor_menus"]


# class TOPBAR_MT_editor_menus(Menu):
#     """
#     I could not find an easy way to simply add the menu into Blender's top
#     menubar.

#     So we use a bit of a hack, by recreating the the same as what blender does
#     to create it's own top level menus but adding the `Shotgun` menu right
#     before `help` menu.

#     Note that If the script to generate those menus was to change in Blender,
#     this would have to be update to reflect the same changes!
#     """
#     bl_idname = "TOPBAR_MT_editor_menus"
#     bl_label = ""

#     def draw(self, _context):
#         layout = self.layout

#         layout.menu("TOPBAR_MT_app", text="", icon='BLENDER')

#         layout.menu("TOPBAR_MT_file")
#         layout.menu("TOPBAR_MT_edit")

#         layout.menu("TOPBAR_MT_render")

#         layout.menu("TOPBAR_MT_window")
#         layout.menu("TOPBAR_MT_shotgun")
#         layout.menu("TOPBAR_MT_help")


def boostrap():
    # start the engine
    SGTK_MODULE_PATH = os.environ.get("SGTK_MODULE_PATH")
    if SGTK_MODULE_PATH and SGTK_MODULE_PATH not in sys.path:
        sys.path.insert(0, SGTK_MODULE_PATH)

    engine_startup_path = os.environ.get("SGTK_BLENDER_ENGINE_STARTUP")
    spec = importlib.util.spec_from_file_location("sgtk_blender_engine_startup", engine_startup_path)
    engine_startup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine_startup)

    # Fire up Toolkit and the environment engine.
    engine_startup.start_toolkit()


@persistent
def startup(dummy):
    global _qt_app
    _qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    if not bpy.app.timers.is_registered(_process_qt_events):
        bpy.app.timers.register(_process_qt_events, persistent=True)
    boostrap()

@persistent
def error_importing_pyside2(*args):
    bpy.ops.shotgun.logger(level="ERROR", message=PYSIDE_MISSING_MESSAGE)


def register():
    bpy.utils.register_class(ShotgunConsoleLog)

    if not PYSIDE_IMPORTED:
        # bpy.app.timers.register(error_importing_pyside2, first_interval=5)
        load_factory_startup_post.append(error_importing_pyside2)
        return

    TOPBAR_MT_help = bpy.types.TOPBAR_MT_help
    TOPBAR_MT_editor_menus = insert_main_menu(
        TOPBAR_MT_shotgun, before_menu_class=TOPBAR_MT_help
    )
    bpy.utils.register_class(TOPBAR_MT_editor_menus)
    bpy.utils.register_class(TOPBAR_MT_shotgun)

    #not sure the reason for using the app handler load_factory_startup_post
    #load_post seems to work as expected vs the shipped functionality
    #load_factory_startup_post.append(startup)
    load_post.append(startup)



def unregister():
    bpy.utils.unregister_class(ShotgunConsoleLog)

    if not PYSIDE_IMPORTED:
        return

    if bpy.app.timers.is_registered(_process_qt_events):
        bpy.app.timers.unregister(_process_qt_events)

    bpy.utils.unregister_class(TOPBAR_MT_shotgun)
