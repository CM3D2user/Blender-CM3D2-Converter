# アドオンを読み込む時に最初にこのファイルが読み込まれます

# アドオン情報
bl_info = {
	"name" : "CM3D2 Converter",
	"author" : "",
	"version" : (0, 365),
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
	
	imp.reload(misc_DATA_PT_context_arm)
	imp.reload(misc_DATA_PT_modifiers)
	imp.reload(misc_DATA_PT_vertex_groups)
	imp.reload(misc_IMAGE_HT_header)
	imp.reload(misc_IMAGE_PT_image_properties)
	imp.reload(misc_INFO_MT_add)
	imp.reload(misc_INFO_MT_curve_add)
	imp.reload(misc_INFO_MT_help)
	imp.reload(misc_MATERIAL_PT_context_material)
	imp.reload(misc_MESH_MT_shape_key_specials)
	imp.reload(misc_MESH_MT_vertex_group_specials)
	imp.reload(misc_OBJECT_PT_context_object)
	imp.reload(misc_OBJECT_PT_transform)
	imp.reload(misc_RENDER_PT_bake)
	imp.reload(misc_RENDER_PT_render)
	imp.reload(misc_TEXTURE_PT_context_texture)
	imp.reload(misc_TEXT_HT_header)
	imp.reload(misc_VIEW3D_MT_pose_apply)

else:
	from . import common
	
	from . import model_import
	from . import model_export
	
	from . import anm_import
	
	from . import tex_import
	from . import tex_export
	
	from . import mate_import
	from . import mate_export
	
	from . import misc_DATA_PT_context_arm
	from . import misc_DATA_PT_modifiers
	from . import misc_DATA_PT_vertex_groups
	from . import misc_IMAGE_HT_header
	from . import misc_IMAGE_PT_image_properties
	from . import misc_INFO_MT_add
	from . import misc_INFO_MT_curve_add
	from . import misc_INFO_MT_help
	from . import misc_MATERIAL_PT_context_material
	from . import misc_MESH_MT_shape_key_specials
	from . import misc_MESH_MT_vertex_group_specials
	from . import misc_OBJECT_PT_context_object
	from . import misc_OBJECT_PT_transform
	from . import misc_RENDER_PT_bake
	from . import misc_RENDER_PT_render
	from . import misc_TEXTURE_PT_context_texture
	from . import misc_TEXT_HT_header
	from . import misc_VIEW3D_MT_pose_apply

import bpy, os.path, bpy.utils.previews

# アドオン設定
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	cm3d2_path = bpy.props.StringProperty(name="CM3D2インストールフォルダ", subtype='DIR_PATH', description="変更している場合は設定しておくと役立つかもしれません")
	backup_ext = bpy.props.StringProperty(name="バックアップの拡張子 (空欄で無効)", description="エクスポート時にバックアップを作成時この拡張子で複製します、空欄でバックアップを無効", default='bak')
	
	scale = bpy.props.FloatProperty(name="倍率", description="Blenderでモデルを扱うときの拡大率", default=5, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2)
	is_convert_bone_weight_names = bpy.props.BoolProperty(name="基本的にボーン名/ウェイト名をBlender用に変換", default=False, description="modelインポート時にボーン名/ウェイト名を変換するかどうかのオプションのデフォルトを設定します")
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
	mate_unread_same_value = bpy.props.BoolProperty(name="同じ設定値が2つ以上ある場合削除", default=True, description="_ShadowColor など")
	mate_import_path = bpy.props.StringProperty(name="mateインポート時のデフォルトパス", subtype='FILE_PATH', description="mateインポート時に最初はここが表示されます、インポート毎に保存されます")
	mate_export_path = bpy.props.StringProperty(name="mateエクスポート時のデフォルトパス", subtype='FILE_PATH', description="mateエクスポート時に最初はここが表示されます、エクスポート毎に保存されます")
	
	is_replace_cm3d2_tex = bpy.props.BoolProperty(name="基本的にtexファイルを探す", default=True, description="texファイルを探すかどうかのオプションのデフォルト値を設定します")
	default_tex_path0 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path1 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path2 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	default_tex_path3 = bpy.props.StringProperty(name="texファイル置き場", subtype='DIR_PATH', description="texファイルを探す時はここから探します")
	
	
	new_mate_tex_color = bpy.props.FloatVectorProperty(name="テクスチャ設定値の色", default=(0, 0, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	
	new_mate_toonramp_name = bpy.props.StringProperty(name="_ToonRamp 名前", default="toonGrayA1")
	new_mate_toonramp_path = bpy.props.StringProperty(name="_ToonRamp パス", default=r"Assets\texture\texture\toon\toonGrayA1.png")
	
	new_mate_shadowratetoon_name = bpy.props.StringProperty(name="_ShadowRateToon 名前", default="toonDress_shadow")
	new_mate_shadowratetoon_path = bpy.props.StringProperty(name="_ShadowRateToon パス", default=r"Assets\texture\texture\toon\toonDress_shadow.png")
	
	new_mate_color = bpy.props.FloatVectorProperty(name="_Color", default=(1, 1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	new_mate_shadowcolor = bpy.props.FloatVectorProperty(name="_ShadowColor", default=(0, 0, 0, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	new_mate_rimcolor = bpy.props.FloatVectorProperty(name="_RimColor", default=(0.5, 0.5, 0.5, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	new_mate_outlinecolor = bpy.props.FloatVectorProperty(name="_OutlineColor", default=(0, 0, 0, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	
	new_mate_shininess = bpy.props.FloatProperty(name="_Shininess", default=0, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	new_mate_outlinewidth = bpy.props.FloatProperty(name="_OutlineWidth", default=0.0015, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	new_mate_rimpower = bpy.props.FloatProperty(name="_RimPower", default=25, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	new_mate_rimshift = bpy.props.FloatProperty(name="_RimShift", default=0, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	new_mate_hirate = bpy.props.FloatProperty(name="_HiRate", default=0.5, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	new_mate_hipow = bpy.props.FloatProperty(name="_HiPow", default=0.001, min=-100, max=100, soft_min=-100, soft_max=100, step=1, precision=2)
	
	def draw(self, context):
		self.layout.label(text="ここの設定は「ユーザー設定の保存」ボタンを押すまで保存されていません", icon='QUESTION')
		self.layout.prop(self, 'cm3d2_path', icon_value=common.preview_collections['main']['KISS'].icon_id)
		self.layout.prop(self, 'backup_ext', icon='FILE_BACKUP')
		
		box = self.layout.box()
		box.label(text="modelファイル", icon='MESH_ICOSPHERE')
		row = box.row()
		row.prop(self, 'scale', icon='MAN_SCALE')
		row.prop(self, 'is_convert_bone_weight_names', icon='BLENDER')
		box.prop(self, 'model_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		
		box = self.layout.box()
		box.label(text="anmファイル", icon='POSE_HLT')
		box.prop(self, 'anm_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		
		box = self.layout.box()
		box.label(text="texファイル", icon='FILE_IMAGE')
		box.prop(self, 'tex_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		
		box = self.layout.box()
		box.label(text="mateファイル", icon='MATERIAL')
		box.prop(self, 'mate_unread_same_value', icon='DISCLOSURE_TRI_DOWN')
		box.prop(self, 'mate_default_path', icon='FILESEL', text="ファイル選択時の初期フォルダ")
		
		box = self.layout.box()
		box.label(text="texファイル検索", icon='BORDERMOVE')
		box.prop(self, 'is_replace_cm3d2_tex', icon='VIEWZOOM')
		box.prop(self, 'default_tex_path0', icon='LAYER_ACTIVE', text="その1")
		box.prop(self, 'default_tex_path1', icon='LAYER_ACTIVE', text="その2")
		box.prop(self, 'default_tex_path2', icon='LAYER_ACTIVE', text="その3")
		box.prop(self, 'default_tex_path3', icon='LAYER_ACTIVE', text="その4")
		
		box = self.layout.box()
		box.label(text="CM3D2用マテリアル新規作成時の初期値", icon='MATERIAL')
		box.prop(self, 'new_mate_tex_color', icon='COLOR')
		row = box.row()
		row.prop(self, 'new_mate_toonramp_name', icon='BRUSH_TEXFILL')
		row.prop(self, 'new_mate_toonramp_path', icon='ANIM')
		row = box.row()
		row.prop(self, 'new_mate_shadowratetoon_name', icon='BRUSH_TEXMASK')
		row.prop(self, 'new_mate_shadowratetoon_path', icon='ANIM')
		row = box.row()
		row.prop(self, 'new_mate_color', icon='COLOR')
		row.prop(self, 'new_mate_shadowcolor', icon='IMAGE_ALPHA')
		row.prop(self, 'new_mate_rimcolor', icon='MATCAP_07')
		row.prop(self, 'new_mate_outlinecolor', icon='SOLID')
		row = box.row()
		row.prop(self, 'new_mate_shininess', icon='MATCAP_05')
		row.prop(self, 'new_mate_outlinewidth', icon='SOLID')
		row.prop(self, 'new_mate_rimpower', icon='MATCAP_14')
		row.prop(self, 'new_mate_rimshift', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'new_mate_hirate')
		row.prop(self, 'new_mate_hipow')
		
		row = self.layout.row()
		row.operator('script.update_cm3d2_converter', icon='FILE_REFRESH')
		row.menu('INFO_MT_help_CM3D2_Converter_RSS', icon='INFO')

# 英訳辞書を作成
def get_english_dictionary():
	try:
		import re, codecs
		
		file_path = os.path.join(os.path.dirname(__file__), "english_dictionary.csv")
		file = codecs.open(file_path, 'r', 'utf-8')
		lines = [re.sub(r'\r?\n$', "", line) for line in file if 2 <= len(line.split('\t'))]
		
		dict = {}
		for locale in bpy.app.translations.locales:
			if locale == 'ja_JP': continue
			dict[locale] = {}
			for line in lines:
				jp, en = line.split('\t')[0], line.split('\t')[1]
				for context in bpy.app.translations.contexts:
					dict[locale][(context, jp)] = en
	except: return {}
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
	
	bpy.types.DATA_PT_context_arm.append(misc_DATA_PT_context_arm.menu_func)
	bpy.types.DATA_PT_modifiers.append(misc_DATA_PT_modifiers.menu_func)
	bpy.types.DATA_PT_vertex_groups.append(misc_DATA_PT_vertex_groups.menu_func)
	bpy.types.IMAGE_HT_header.append(misc_IMAGE_HT_header.menu_func)
	bpy.types.IMAGE_PT_image_properties.append(misc_IMAGE_PT_image_properties.menu_func)
	bpy.types.INFO_MT_add.append(misc_INFO_MT_add.menu_func)
	bpy.types.INFO_MT_curve_add.append(misc_INFO_MT_curve_add.menu_func)
	bpy.types.INFO_MT_help.append(misc_INFO_MT_help.menu_func)
	bpy.types.MATERIAL_PT_context_material.append(misc_MATERIAL_PT_context_material.menu_func)
	bpy.types.MESH_MT_shape_key_specials.append(misc_MESH_MT_shape_key_specials.menu_func)
	bpy.types.MESH_MT_vertex_group_specials.append(misc_MESH_MT_vertex_group_specials.menu_func)
	bpy.types.OBJECT_PT_context_object.append(misc_OBJECT_PT_context_object.menu_func)
	bpy.types.OBJECT_PT_transform.append(misc_OBJECT_PT_transform.menu_func)
	bpy.types.RENDER_PT_bake.append(misc_RENDER_PT_bake.menu_func)
	bpy.types.RENDER_PT_render.append(misc_RENDER_PT_render.menu_func)
	bpy.types.TEXTURE_PT_context_texture.append(misc_TEXTURE_PT_context_texture.menu_func)
	bpy.types.TEXT_HT_header.append(misc_TEXT_HT_header.menu_func)
	bpy.types.VIEW3D_MT_pose_apply.append(misc_VIEW3D_MT_pose_apply.menu_func)
	
	pcoll = bpy.utils.previews.new()
	dir = os.path.dirname(__file__)
	pcoll.load('KISS', os.path.join(dir, "kiss.png"), 'IMAGE')
	common.preview_collections['main'] = pcoll
	
	system = bpy.context.user_preferences.system
	if not system.use_international_fonts:
		system.use_international_fonts = True
	if not system.use_translate_interface:
		system.use_translate_interface = True
	try:
		import locale
		if system.language == 'DEFAULT' and locale.getdefaultlocale()[0] != 'ja_JP':
			system.language = 'en_US'
	except: pass
	
	bpy.app.translations.register(__name__, get_english_dictionary())

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
	
	bpy.types.DATA_PT_context_arm.remove(misc_DATA_PT_context_arm.menu_func)
	bpy.types.DATA_PT_modifiers.remove(misc_DATA_PT_modifiers.menu_func)
	bpy.types.DATA_PT_vertex_groups.remove(misc_DATA_PT_vertex_groups.menu_func)
	bpy.types.IMAGE_HT_header.remove(misc_IMAGE_HT_header.menu_func)
	bpy.types.IMAGE_PT_image_properties.remove(misc_IMAGE_PT_image_properties.menu_func)
	bpy.types.INFO_MT_add.remove(misc_INFO_MT_add.menu_func)
	bpy.types.INFO_MT_curve_add.remove(misc_INFO_MT_curve_add.menu_func)
	bpy.types.INFO_MT_help.remove(misc_INFO_MT_help.menu_func)
	bpy.types.MATERIAL_PT_context_material.remove(misc_MATERIAL_PT_context_material.menu_func)
	bpy.types.MESH_MT_shape_key_specials.remove(misc_MESH_MT_shape_key_specials.menu_func)
	bpy.types.MESH_MT_vertex_group_specials.remove(misc_MESH_MT_vertex_group_specials.menu_func)
	bpy.types.OBJECT_PT_context_object.remove(misc_OBJECT_PT_context_object.menu_func)
	bpy.types.OBJECT_PT_transform.remove(misc_OBJECT_PT_transform.menu_func)
	bpy.types.RENDER_PT_bake.remove(misc_RENDER_PT_bake.menu_func)
	bpy.types.RENDER_PT_render.remove(misc_RENDER_PT_render.menu_func)
	bpy.types.TEXTURE_PT_context_texture.remove(misc_TEXTURE_PT_context_texture.menu_func)
	bpy.types.TEXT_HT_header.remove(misc_TEXT_HT_header.menu_func)
	bpy.types.VIEW3D_MT_pose_apply.remove(misc_VIEW3D_MT_pose_apply.menu_func)
	
	for pcoll in common.preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	common.preview_collections.clear()
	
	bpy.app.translations.unregister(__name__)

# メイン関数
if __name__ == "__main__":
	register()
