# アドオンを読み込む時に最初にこのファイルが読み込まれます

# アドオン情報
bl_info = {
	"name" : "CM3D2 Converter",
	"author" : "",
	"version" : (0, 123),
	"blender" : (2, 7),
	"location" : "ファイル > インポート/エクスポート > CM3D2 Model (.model)",
	"description" : "カスタムメイド3D2の専用ファイルのインポート/エクスポートを行います",
	"warning" : "",
	"wiki_url" : "https://github.com/CM3Duser/Blender-CM3D2-Converter",
	"tracker_url" : "http://jbbs.shitaraba.net/bbs/subject.cgi/game/55179/?q=%A1%D6%A5%AB%A5%B9%A5%BF%A5%E0%A5%E1%A5%A4%A5%C93D2%A1%D7%B2%FE%C2%A4%A5%B9%A5%EC%A5%C3%A5%C9",
	"category" : "Import-Export"
}

# サブスクリプト群をインポート
if "bpy" in locals():
	import imp
	
	imp.reload(common)
	
	imp.reload(model_import)
	imp.reload(model_export)
	
	imp.reload(anm_import)
	
	imp.reload(tex_import)
	imp.reload(tex_export)
	
	imp.reload(mate_import)
	imp.reload(mate_export)
	
	imp.reload(misc_menus)
	imp.reload(misc_tools)
else:
	from . import common
	
	from . import model_import
	from . import model_export
	
	from . import anm_import
	
	from . import tex_import
	from . import tex_export
	
	from . import mate_import
	from . import mate_export
	
	from . import misc_menus
	from . import misc_tools
import bpy, os.path, bpy.utils.previews

# アドオン設定
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	cm3d2_path = bpy.props.StringProperty(name="CM3D2インストールフォルダ", subtype='DIR_PATH', description="変更している場合は設定しておくと役立つかもしれません")
	backup_ext = bpy.props.StringProperty(name="バックアップの拡張子 (空欄で無効)", description="エクスポート時にバックアップを作成時この拡張子で複製します、空欄でバックアップを無効", default='bak')
	
	scale = bpy.props.FloatProperty(name="倍率", description="Blenderでモデルを扱うときの拡大率", default=5, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2)
	model_default_path = bpy.props.StringProperty(name="modelファイル置き場", subtype='DIR_PATH', description="設定すれば、modelを扱う時は必ずここからファイル選択を始めます")
	model_import_path = bpy.props.StringProperty(name="modelインポート時のデフォルトパス", subtype='FILE_PATH', description="modelインポート時に最初はここが表示されます、インポート毎に保存されます")
	model_export_path = bpy.props.StringProperty(name="modelエクスポート時のデフォルトパス", subtype='FILE_PATH', description="modelエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	anm_default_path = bpy.props.StringProperty(name="anmファイル置き場", subtype='DIR_PATH', description="設定すれば、anmを扱う時は必ずここからファイル選択を始めます")
	anm_import_path = bpy.props.StringProperty(name="anmインポート時のデフォルトパス", subtype='FILE_PATH', description="anmインポート時に最初はここが表示されます、インポート毎に保存されます")
	anm_export_path = bpy.props.StringProperty(name="anmエクスポート時のデフォルトパス", subtype='FILE_PATH', description="anmエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	tex_default_path = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="設定すれば、texを扱う時は必ずここからファイル選択を始めます")
	tex_import_path = bpy.props.StringProperty(name="texインポート時のデフォルトパス", subtype='FILE_PATH', description="texインポート時に最初はここが表示されます、インポート毎に保存されます")
	tex_export_path = bpy.props.StringProperty(name="texエクスポート時のデフォルトパス", subtype='FILE_PATH', description="texエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	mate_default_path = bpy.props.StringProperty(name="mateファイル置き場", subtype='DIR_PATH', description="設定すれば、mateを扱う時は必ずここからファイル選択を始めます")
	mate_import_path = bpy.props.StringProperty(name="mateインポート時のデフォルトパス", subtype='FILE_PATH', description="mateインポート時に最初はここが表示されます、インポート毎に保存されます")
	mate_export_path = bpy.props.StringProperty(name="mateエクスポート時のデフォルトパス", subtype='FILE_PATH', description="mateエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	default_tex_path0 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path1 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path2 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path3 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	
	def draw(self, context):
		self.layout.label(text="ここの設定は「ユーザー設定の保存」ボタンを押すまで保存されていません", icon='QUESTION')
		self.layout.prop(self, 'cm3d2_path', icon_value=common.preview_collections['main']['KISS'].icon_id)
		self.layout.prop(self, 'backup_ext', icon='FILE_BACKUP')
		box = self.layout.box()
		box.label(text="modelファイル", icon='MESH_ICOSPHERE')
		box.prop(self, 'scale', icon='MAN_SCALE')
		box.prop(self, 'model_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		box = self.layout.box()
		box.label(text="anmファイル", icon='POSE_HLT')
		box.prop(self, 'anm_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		box = self.layout.box()
		box.label(text="texファイル", icon='FILE_IMAGE')
		box.prop(self, 'tex_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		box = self.layout.box()
		box.label(text="mateファイル", icon='MATERIAL')
		box.prop(self, 'mate_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		box = self.layout.box()
		box.label(text="texファイル置き場", icon='BORDERMOVE')
		box.prop(self, 'default_tex_path0', icon='TEXTURE', text="その1")
		box.prop(self, 'default_tex_path1', icon='TEXTURE', text="その2")
		box.prop(self, 'default_tex_path2', icon='TEXTURE', text="その3")
		box.prop(self, 'default_tex_path3', icon='TEXTURE', text="その4")
		row = self.layout.row()
		row.operator('script.update_cm3d2_converter', icon='FILE_REFRESH')
		row.menu('INFO_MT_help_CM3D2_Converter_RSS', icon='INFO')

# 英訳辞書を作成
def get_english_dictionary():
	try:
		import re, codecs
		
		addon_dir = os.path.dirname(__file__)
		file_path = os.path.join(addon_dir, "english_dictionary.csv")
		
		file = codecs.open(file_path, 'r', 'utf-8')
		lines = [re.sub(r'\r?\n$', "", line) for line in file if re.sub(r'\r?\n$', "", line)]
		
		dict = {}
		for locale in bpy.app.translations.locales:
			if locale == 'ja_JP':
				continue
			dict[locale] = {}
			for line in lines:
				jp, en = line.split('\t')
				for context in bpy.app.translations.contexts:
					dict[locale][(context, jp)] = en
	except:
		dict = {}
	return dict

# プラグインをインストールしたときの処理
def register():
	bpy.utils.register_module(__name__)
	
	bpy.types.INFO_MT_file_import.append(model_import.menu_func)
	bpy.types.INFO_MT_file_export.append(model_export.menu_func)
	
	bpy.types.INFO_MT_file_import.append(anm_import.menu_func)
	
	bpy.types.IMAGE_MT_image.append(tex_import.menu_func)
	bpy.types.IMAGE_MT_image.append(tex_export.menu_func)
	
	bpy.types.TEXT_MT_text.append(mate_import.TEXT_MT_text)
	bpy.types.TEXT_MT_text.append(mate_export.TEXT_MT_text)
	
	bpy.types.DATA_PT_context_arm.append(misc_menus.DATA_PT_context_arm)
	bpy.types.DATA_PT_modifiers.append(misc_menus.DATA_PT_modifiers)
	bpy.types.DATA_PT_vertex_groups.append(misc_menus.DATA_PT_vertex_groups)
	bpy.types.IMAGE_HT_header.append(misc_menus.IMAGE_HT_header)
	bpy.types.IMAGE_PT_image_properties.append(misc_menus.IMAGE_PT_image_properties)
	bpy.types.INFO_MT_help.append(misc_menus.INFO_MT_help)
	bpy.types.MATERIAL_PT_context_material.append(misc_menus.MATERIAL_PT_context_material)
	bpy.types.MESH_MT_shape_key_specials.append(misc_menus.MESH_MT_shape_key_specials)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_menus.MESH_MT_vertex_group_specials)
	bpy.types.OBJECT_PT_context_object.append(misc_menus.OBJECT_PT_context_object)
	bpy.types.OBJECT_PT_transform.append(misc_menus.OBJECT_PT_transform)
	bpy.types.TEXTURE_PT_context_texture.append(misc_menus.TEXTURE_PT_context_texture)
	bpy.types.TEXT_HT_header.append(misc_menus.TEXT_HT_header)
	
	pcoll = bpy.utils.previews.new()
	dir = os.path.dirname(__file__)
	pcoll.load('KISS', os.path.join(dir, "kiss.png"), 'IMAGE')
	common.preview_collections['main'] = pcoll
	
	if not bpy.context.user_preferences.system.use_international_fonts:
		bpy.context.user_preferences.system.use_international_fonts = True
	
	bpy.app.translations.register(__name__, get_english_dictionary())
	# 余計なお世話
	dict = { 'ja_JP':{('Operator', "Apply All Modifier"):"全モディファイアを適用", ('Operator', "Apply Selected Modifier"):"選択モディファイアを適用", ('Operator', "Apply_Selected_Modifier"):"選択モディファイアを適用"} }
	bpy.app.translations.register("Apply Modifier", dict)

# プラグインをアンインストールしたときの処理
def unregister():
	bpy.utils.unregister_module(__name__)
	
	bpy.types.INFO_MT_file_import.remove(model_import.menu_func)
	bpy.types.INFO_MT_file_export.remove(model_export.menu_func)
	
	bpy.types.INFO_MT_file_import.remove(anm_import.menu_func)
	
	bpy.types.IMAGE_MT_image.remove(tex_import.menu_func)
	bpy.types.IMAGE_MT_image.remove(tex_export.menu_func)
	
	bpy.types.TEXT_MT_text.remove(mate_import.TEXT_MT_text)
	bpy.types.TEXT_MT_text.remove(mate_export.TEXT_MT_text)
	
	bpy.types.DATA_PT_context_arm.remove(misc_menus.DATA_PT_context_arm)
	bpy.types.DATA_PT_modifiers.remove(misc_menus.DATA_PT_modifiers)
	bpy.types.DATA_PT_vertex_groups.remove(misc_menus.DATA_PT_vertex_groups)
	bpy.types.IMAGE_HT_header.remove(misc_menus.IMAGE_HT_header)
	bpy.types.IMAGE_PT_image_properties.remove(misc_menus.IMAGE_PT_image_properties)
	bpy.types.INFO_MT_help.remove(misc_menus.INFO_MT_help)
	bpy.types.MATERIAL_PT_context_material.remove(misc_menus.MATERIAL_PT_context_material)
	bpy.types.MESH_MT_shape_key_specials.remove(misc_menus.MESH_MT_shape_key_specials)
	bpy.types.MESH_MT_vertex_group_specials.remove(misc_menus.MESH_MT_vertex_group_specials)
	bpy.types.OBJECT_PT_context_object.remove(misc_menus.OBJECT_PT_context_object)
	bpy.types.OBJECT_PT_transform.remove(misc_menus.OBJECT_PT_transform)
	bpy.types.TEXTURE_PT_context_texture.remove(misc_menus.TEXTURE_PT_context_texture)
	bpy.types.TEXT_HT_header.remove(misc_menus.TEXT_HT_header)
	
	for pcoll in common.preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	common.preview_collections.clear()
	
	bpy.app.translations.unregister(__name__)
	bpy.app.translations.unregister("Apply Modifier")

# メイン関数
if __name__ == "__main__":
	register()
