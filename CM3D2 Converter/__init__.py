# アドオンを読み込む時に最初にこのファイルが読み込まれます

# アドオン情報
bl_info = {
	"name" : "CM3D2 Converter",
	"author" : "",
	"version" : (0, 1),
	"blender" : (2, 7),
	"location" : "ファイル > インポート/エクスポート > CM3D2 Model (.model)",
	"description" : "カスタムメイド3D2の専用ファイルのインポート/エクスポートを行います",
	"warning" : "",
	"wiki_url" : "https://github.com/CM3Duser/Blender-CM3D2-Converter",
	"tracker_url" : "http://jbbs.shitaraba.net/game/55179/",
	"category" : "Import-Export"
}

# サブスクリプト群をインポート
if "bpy" in locals():
	import imp
	imp.reload(model_import)
	imp.reload(model_export)
	imp.reload(tex_import)
	imp.reload(misc_tools)
else:
	from . import model_import
	from . import model_export
	from . import tex_import
	from . import misc_tools
import bpy

# アドオン設定
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	scale = bpy.props.FloatProperty(name="倍率", description="Blenderでモデルを扱うときの拡大率", default=5, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2)
	
	model_import_path = bpy.props.StringProperty(name="modelインポート時のデフォルトパス", subtype='FILE_PATH', description="modelインポート時に最初はここが表示されます、インポート毎に保存されます")
	model_export_path = bpy.props.StringProperty(name="modelエクスポート時のデフォルトパス", subtype='FILE_PATH', description="modelエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	tex_import_path = bpy.props.StringProperty(name="texインポート時のデフォルトパス", subtype='FILE_PATH', description="texインポート時に最初はここが表示されます、インポート毎に保存されます")
	
	backup_ext = bpy.props.StringProperty(name="バックアップの拡張子 (空欄で無効)", description="エクスポート時にバックアップを作成時この拡張子で複製します、空欄でバックアップを無効", default='bak')
	
	def draw(self, context):
		self.layout.prop(self, 'scale', icon='MAN_SCALE')
		self.layout.prop(self, 'model_import_path', icon='IMPORT')
		self.layout.prop(self, 'model_export_path', icon='EXPORT')
		self.layout.prop(self, 'tex_import_path', icon='IMAGE_DATA')
		self.layout.prop(self, 'backup_ext', icon='FILE_BACKUP')
		self.layout.operator(update_cm3d2_converter.bl_idname, icon='FILE_REFRESH')

# プラグインをインストールしたときの処理
def register():
	bpy.utils.register_module(__name__)
	
	bpy.types.INFO_MT_file_import.append(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	bpy.types.IMAGE_MT_image.append(tex_import.menu_func)
	
	bpy.types.INFO_MT_help.append(misc_tools.INFO_MT_help)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_tools.MESH_MT_vertex_group_specials)
	bpy.types.MESH_MT_shape_key_specials.append(misc_tools.MESH_MT_shape_key_specials)
	bpy.types.MATERIAL_PT_context_material.append(misc_tools.MATERIAL_PT_context_material)
	bpy.types.DATA_PT_context_arm.append(misc_tools.DATA_PT_context_arm)
	bpy.types.TEXTURE_PT_context_texture.append(misc_tools.TEXTURE_PT_context_texture)
	bpy.types.OBJECT_PT_context_object.append(misc_tools.OBJECT_PT_context_object)
	bpy.types.DATA_PT_modifiers.append(misc_tools.DATA_PT_modifiers)
	bpy.types.TEXT_HT_header.append(misc_tools.TEXT_HT_header)

# プラグインをアンインストールしたときの処理
def unregister():
	bpy.utils.unregister_module(__name__)
	
	bpy.types.INFO_MT_file_import.remove(model_import.menu_func)
	bpy.types.INFO_MT_file_export.remove(model_export.menu_func)
	bpy.types.IMAGE_MT_image.remove(tex_import.menu_func)
	
	bpy.types.INFO_MT_help.remove(misc_tools.INFO_MT_help)
	bpy.types.MESH_MT_shape_key_specials.remove(misc_tools.MESH_MT_shape_key_specials)
	bpy.types.MESH_MT_vertex_group_specials.remove(misc_tools.MESH_MT_vertex_group_specials)
	bpy.types.MATERIAL_PT_context_material.remove(misc_tools.MATERIAL_PT_context_material)
	bpy.types.DATA_PT_context_arm.remove(misc_tools.DATA_PT_context_arm)
	bpy.types.TEXTURE_PT_context_texture.remove(misc_tools.TEXTURE_PT_context_texture)
	bpy.types.OBJECT_PT_context_object.remove(misc_tools.OBJECT_PT_context_object)
	bpy.types.DATA_PT_modifiers.remove(misc_tools.DATA_PT_modifiers)
	bpy.types.TEXT_HT_header.remove(misc_tools.TEXT_HT_header)

# メイン関数
if __name__ == "__main__":
	register()
