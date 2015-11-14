# アドオンを読み込む時に最初にこのファイルが読み込まれます

import os, sys, urllib, zipfile, subprocess, urllib.request

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
	imp.reload(misc_tools)
else:
	from . import model_import
	from . import model_export
	from . import misc_tools
import bpy

# アドオン設定
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	scale = bpy.props.FloatProperty(name="倍率", description="Blenderでモデルを扱うときの拡大率", default=5, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2)
	
	model_import_path = bpy.props.StringProperty(name="Modelインポート時のデフォルトパス", subtype='FILE_PATH', description="インポート時に最初はここが表示されます、インポート毎に保存されます")
	model_export_path = bpy.props.StringProperty(name="Modelエクスポート時のデフォルトパス", subtype='FILE_PATH', description="エクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	backup_ext = bpy.props.StringProperty(name="バックアップの拡張子 (空欄で無効)", description="エクスポート時にバックアップを作成時この拡張子で複製します、空欄でバックアップを無効", default='bak')
	
	def draw(self, context):
		self.layout.prop(self, 'scale', icon='MAN_SCALE')
		self.layout.prop(self, 'model_import_path', icon='IMPORT')
		self.layout.prop(self, 'model_export_path', icon='EXPORT')
		self.layout.prop(self, 'backup_ext', icon='FILE_BACKUP')
		self.layout.operator(update_cm3d2_converter.bl_idname, icon='FILE_REFRESH')

# アドオンアップデート処理
class update_cm3d2_converter(bpy.types.Operator):
	bl_idname = 'script.update_cm3d2_converter'
	bl_label = "Blender-CM3D2-Converterを更新"
	bl_description = "GitHubから最新版のBlender-CM3D2-Converterをダウンロードし上書きします、実行した後は再起動して下さい"
	bl_options = {'REGISTER'}
	
	is_restart = bpy.props.BoolProperty(name="更新後にBlenderを再起動", description="アドオン更新後にBlenderを再起動します", default=True)
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_restart')
	
	def execute(self, context):
		response = urllib.request.urlopen("https://github.com/CM3Duser/Blender-CM3D2-Converter/archive/master.zip")
		tempDir = bpy.app.tempdir
		zipPath = os.path.join(tempDir, "Blender-CM3D2-Converter-master.zip")
		addonDir = os.path.dirname(__file__)
		f = open(zipPath, "wb")
		f.write(response.read())
		f.close()
		zf = zipfile.ZipFile(zipPath, "r")
		for f in zf.namelist():
			if not os.path.basename(f):
				pass
			else:
				if ("CM3D2 Converter" in f):
					uzf = open(os.path.join(addonDir, os.path.basename(f)), 'wb')
					uzf.write(zf.read(f))
					uzf.close()
		zf.close()
		if self.is_restart:
			subprocess.Popen([sys.argv[0]])
			bpy.ops.wm.quit_blender()
		else:
			self.report(type={'WARNING'}, message="Blender-CM3D2-Converterを更新しました、再起動して下さい")
		return {'FINISHED'}

# ヘルプメニューに項目追加
def INFO_MT_help(self, context):
	self.layout.separator()
	self.layout.operator(update_cm3d2_converter.bl_idname, icon='SPACE2')

# プラグインをインストールしたときの処理
def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_help.append(INFO_MT_help)
	bpy.types.INFO_MT_file_import.append(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_tools.MESH_MT_vertex_group_specials)
	bpy.types.MESH_MT_shape_key_specials.append(misc_tools.MESH_MT_shape_key_specials)
	bpy.types.MATERIAL_PT_context_material.append(misc_tools.MATERIAL_PT_context_material)
	bpy.types.DATA_PT_context_arm.append(misc_tools.DATA_PT_context_arm)
	bpy.types.TEXTURE_PT_context_texture.append(misc_tools.TEXTURE_PT_context_texture)

# プラグインをアンインストールしたときの処理
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_help.remove(INFO_MT_help)
	bpy.types.INFO_MT_file_import.remove(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	bpy.types.MESH_MT_shape_key_specials.append(misc_tools.MESH_MT_shape_key_specials)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_tools.MESH_MT_vertex_group_specials)
	bpy.types.MATERIAL_PT_context_material.append(misc_tools.MATERIAL_PT_context_material)
	bpy.types.DATA_PT_context_arm.append(misc_tools.DATA_PT_context_arm)
	bpy.types.TEXTURE_PT_context_texture.append(misc_tools.TEXTURE_PT_context_texture)

# メイン関数
if __name__ == "__main__":
	register()
