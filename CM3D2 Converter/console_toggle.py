import bpy
bpy.ops.wm.console_toggle()
def draw(self, context):
	self.layout.label("CM3D2 Converterの更新が完了しました")
bpy.context.window_manager.popup_menu(draw, title="CM3D2 Converter", icon='INFO')
