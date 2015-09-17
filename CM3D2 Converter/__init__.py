# アドオンを読み込む時に最初にこのファイルが読み込まれます

import os, urllib, zipfile

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
	
	model_import_path = bpy.props.StringProperty(name="Modelインポート時のデフォルトパス", subtype='FILE_PATH', description="インポート時に最初はここが表示されます、インポート毎に保存されます")
	model_export_path = bpy.props.StringProperty(name="Modelエクスポート時のデフォルトパス", subtype='FILE_PATH', description="エクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	backup_ext = bpy.props.StringProperty(name="バックアップの拡張子", description="エクスポート時にバックアップを作成時この拡張子で複製します、空欄でバックアップを無効", default='bak')
	
	def draw(self, context):
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
		self.report(type={'WARNING'}, message="Blender-CM3D2-Converterを更新しました、再起動して下さい")
		return {'FINISHED'}

# プラグインをインストールしたときの処理
def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_tools.MESH_MT_vertex_group_specials)
	bpy.types.MESH_MT_shape_key_specials.append(misc_tools.MESH_MT_shape_key_specials)

# プラグインをアンインストールしたときの処理
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	bpy.types.MESH_MT_shape_key_specials.append(misc_tools.MESH_MT_shape_key_specials)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_tools.MESH_MT_vertex_group_specials)

# メイン関数
if __name__ == "__main__":
	register()
