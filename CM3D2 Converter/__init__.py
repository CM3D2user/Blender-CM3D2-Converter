# アドオンを読み込む時に最初にこのファイルが読み込まれます

# アドオン情報
bl_info = {
	"name" : "CM3D2 Converter",
	"author" : "",
	"version" : (0, 1),
	"blender" : (2, 7),
	"location" : "File => Import/Export => CM3D2...",
	"description" : "カスタムメイド3D2の専用ファイルのインポート/エクスポートを行います",
	"warning" : "",
	"wiki_url" : "",
	"tracker_url" : "",
	"category" : "Import-Export"
}

# サブスクリプト群をインポート
if "bpy" in locals():
	import imp
	imp.reload(model_import)
else:
	from . import model_import
import bpy

# アドオン設定
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	model_import_path = bpy.props.StringProperty(name="Modelインポート時のデフォルトパス", subtype="FILE_PATH")
	
	def draw(self, context):
		self.layout.prop(self, 'model_import_path')

# プラグインをインストールしたときの処理
def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(model_import.menu_func)

# プラグインをアンインストールしたときの処理
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(model_import.menu_func)

# メイン関数
if __name__ == "__main__":
	register()
